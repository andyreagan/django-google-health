"""Map Google Health API payloads onto django-healthdatamodel records.

Mappers cover the beachhead data types:

  steps, total-calories, heart-rate, weight  → :class:`RecordInput` (Sample/Interval)
  sleep                                       → list[:class:`RecordInput`] (one per stage)
  exercise                                    → :class:`WorkoutInput`

Plus the secondary set: distance, altitude, floors, active-zone-minutes,
daily-resting-heart-rate, daily-oxygen-saturation, body-fat.

Caveats — Google Health's data model isn't 1:1 with Apple HealthKit (which is what
``healthdatamodel`` schemas mirror):

* Google exposes a single ``total-calories`` type. We map it to
  ``ActivityMetric.ACTIVE_CALORIES`` because that's the closest semantic match
  (Fitbit's caloriesOut historically lands there). ``BASAL_CALORIES`` is not
  available from the Google Health API.
* ``HKAltitudeGain`` is a non-standard identifier — Apple HealthKit doesn't have
  a direct analog for cumulative elevation gain over an interval.

The high-level orchestrator is :func:`sync_user`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, Callable

import dateutil.parser
from healthdatamodel.bmr import age_from_dob, calculate_bmr, get_bmr
from healthdatamodel.constants import DataSource
from healthdatamodel.ingest import ingest_records, ingest_workouts
from healthdatamodel.models import Record
from healthdatamodel.query import SLEEP_TYPE, ActivityMetric, SleepValue
from healthdatamodel.schemas import MetadataEntry, RecordInput, WorkoutInput

from .client import GoogleHealthClient
from .constants import (
    DATA_TYPE_ACTIVE_ZONE_MINUTES,
    DATA_TYPE_ALTITUDE,
    DATA_TYPE_BODY_FAT,
    DATA_TYPE_DAILY_OXYGEN_SATURATION,
    DATA_TYPE_DAILY_RESTING_HEART_RATE,
    DATA_TYPE_DISTANCE,
    DATA_TYPE_EXERCISE,
    DATA_TYPE_FLOORS,
    DATA_TYPE_HEART_RATE,
    DATA_TYPE_HEIGHT,
    DATA_TYPE_SLEEP,
    DATA_TYPE_STEPS,
    DATA_TYPE_TOTAL_CALORIES,
    DATA_TYPE_WEIGHT,
    SOURCE_NAME,
)

if TYPE_CHECKING:
    from .models import GoogleHealthConnection

# Apple HealthKit identifiers not exported as enum members in healthdatamodel.
HK_HEART_RATE = "HKQuantityTypeIdentifierHeartRate"
HK_BODY_MASS = "HKQuantityTypeIdentifierBodyMass"
HK_DISTANCE_WALKING_RUNNING = "HKQuantityTypeIdentifierDistanceWalkingRunning"
HK_FLIGHTS_CLIMBED = "HKQuantityTypeIdentifierFlightsClimbed"
HK_ALTITUDE_GAIN = (
    "HKQuantityTypeIdentifierAltitudeGain"  # non-standard; closest mirror
)
HK_ACTIVE_ZONE_MINUTES = "HKQuantityTypeIdentifierAppleExerciseTime"
HK_RESTING_HEART_RATE = "HKQuantityTypeIdentifierRestingHeartRate"
HK_OXYGEN_SATURATION = "HKQuantityTypeIdentifierOxygenSaturation"
HK_BODY_FAT_PERCENTAGE = "HKQuantityTypeIdentifierBodyFatPercentage"
HK_HEIGHT = "HKQuantityTypeIdentifierHeight"

# Map Google's sleep stage strings → healthdatamodel SleepValue. Two known
# stage taxonomies in the wild:
#   * STAGES sleep type — LIGHT / DEEP / REM / AWAKE / IN_BED (or OUT_OF_BED)
#   * CLASSIC sleep type — only ASLEEP / AWAKE / RESTLESS (no granularity)
# Stage label lives at ``stages[].type`` (not ``stages[].stage``).
_SLEEP_STAGE_MAP: dict[str, str] = {
    "LIGHT": SleepValue.ASLEEP_CORE,
    "DEEP": SleepValue.ASLEEP_DEEP,
    "REM": SleepValue.ASLEEP_REM,
    "AWAKE": SleepValue.AWAKE,
    "IN_BED": SleepValue.IN_BED,
    "UNSPECIFIED": SleepValue.ASLEEP_UNSPECIFIED,
    "OUT_OF_BED": SleepValue.AWAKE,
    # CLASSIC sleep type — coarse-grained
    "ASLEEP": SleepValue.ASLEEP_UNSPECIFIED,
    "RESTLESS": SleepValue.AWAKE,
}


@dataclass
class SyncResult:
    """Per-type counts returned by :func:`sync_user`."""

    counts: dict[str, int] = field(default_factory=dict)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None

    @property
    def total(self) -> int:
        return sum(self.counts.values())


def _parse_dt(value: str | None) -> datetime:
    if not value:
        raise ValueError("missing datetime value")
    # Google returns RFC3339 with Z suffix, e.g. "2026-02-23T13:10:00Z".
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _record_id(data_point: dict[str, Any]) -> str | None:
    # Last segment of "users/{id}/dataTypes/{type}/dataPoints/{record_id}"
    name = data_point.get("name")
    if not name:
        return None
    return name.rsplit("/", 1)[-1]


def _interval_bounds(value: dict[str, Any]) -> tuple[datetime, datetime]:
    interval = value.get("interval") or {}
    return _parse_dt(interval.get("startTime")), _parse_dt(interval.get("endTime"))


def _common_record_fields(data_point: dict[str, Any]) -> dict[str, Any]:
    return {
        "recordId": _record_id(data_point),
        "creationDate": _creation_date(data_point),
        "sourceName": SOURCE_NAME,
    }


def _creation_date(data_point: dict[str, Any]) -> datetime:
    """Pick the best available timestamp for ``Record.creationDate``.

    Google's list response often omits ``updateTime`` — only get-by-id calls
    include it. Fall back to the interval start / sampleTime, then to ``now()``.
    """
    for block in data_point.values():
        if not isinstance(block, dict):
            continue
        if "updateTime" in block:
            return _parse_dt(block["updateTime"])
        interval = block.get("interval")
        if isinstance(interval, dict) and "startTime" in interval:
            return _parse_dt(interval["startTime"])
        sample = block.get("sampleTime")
        if isinstance(sample, dict) and "physicalTime" in sample:
            return _parse_dt(sample["physicalTime"])
    return datetime.now(timezone.utc)


def _sample_instant(block: dict[str, Any]) -> datetime:
    """Resolve the point-in-time for a Sample data type.

    Production payload: ``{"sampleTime": {"physicalTime": "...Z", ...}}``.
    Earlier drafts of this code expected a flat ``"time"`` field; we accept
    either for resilience.
    """
    sample_time = block.get("sampleTime")
    if isinstance(sample_time, dict) and sample_time.get("physicalTime"):
        return _parse_dt(sample_time["physicalTime"])
    if block.get("time"):
        return _parse_dt(block["time"])
    raise ValueError("Sample data point has no sampleTime.physicalTime or time field")


# Mappers ---------------------------------------------------------------------


def map_steps(data_point: dict[str, Any]) -> RecordInput:
    block = data_point["steps"]
    start, end = _interval_bounds(block)
    # Live payload uses "count"; earlier drafts assumed "stepCount" — accept both.
    count = block.get("count") or block.get("stepCount") or "0"
    return RecordInput(
        **_common_record_fields(data_point),
        startDate=start,
        endDate=end,
        type=str(ActivityMetric.STEPS),
        value=str(count),
        unit="count",
    )


def map_total_calories(data_point: dict[str, Any]) -> RecordInput:
    block = data_point["totalCalories"]
    start, end = _interval_bounds(block)
    return RecordInput(
        **_common_record_fields(data_point),
        startDate=start,
        endDate=end,
        type=str(ActivityMetric.ACTIVE_CALORIES),
        value=str(block.get("caloriesKcal", "0")),
        unit="kcal",
    )


def map_heart_rate(data_point: dict[str, Any]) -> RecordInput:
    block = data_point["heartRate"]
    instant = _sample_instant(block)
    return RecordInput(
        **_common_record_fields(data_point),
        startDate=instant,
        endDate=instant,
        type=HK_HEART_RATE,
        value=str(block.get("beatsPerMinute", "0")),
        unit="count/min",
    )


def map_weight(data_point: dict[str, Any]) -> RecordInput:
    block = data_point["weight"]
    instant = _sample_instant(block)
    # Live payload uses weightGrams (integer); accept weightKg for back-compat.
    if "weightGrams" in block:
        weight_kg = float(block["weightGrams"]) / 1000.0
    else:
        weight_kg = float(block.get("weightKg", 0))
    return RecordInput(
        **_common_record_fields(data_point),
        startDate=instant,
        endDate=instant,
        type=HK_BODY_MASS,
        value=str(weight_kg),
        unit="kg",
    )


def map_distance(data_point: dict[str, Any]) -> RecordInput:
    """Distance accumulated over an Interval. Google reports millimeters."""
    block = data_point["distance"]
    start, end = _interval_bounds(block)
    distance_mm = float(
        block.get("distanceMillimeters") or block.get("distanceMillimiters") or 0
    )
    return RecordInput(
        **_common_record_fields(data_point),
        startDate=start,
        endDate=end,
        type=HK_DISTANCE_WALKING_RUNNING,
        value=str(distance_mm / 1000.0),
        unit="m",
    )


def map_altitude(data_point: dict[str, Any]) -> RecordInput:
    """Elevation gained over an Interval. Google reports millimeters."""
    block = data_point["altitude"]
    start, end = _interval_bounds(block)
    altitude_mm = float(
        block.get("elevationGainMillimeters")
        or block.get("elevationGainMillimiters")
        or 0
    )
    return RecordInput(
        **_common_record_fields(data_point),
        startDate=start,
        endDate=end,
        type=HK_ALTITUDE_GAIN,
        value=str(altitude_mm / 1000.0),
        unit="m",
    )


def map_floors(data_point: dict[str, Any]) -> RecordInput:
    """Floors climbed over an Interval."""
    block = data_point["floors"]
    start, end = _interval_bounds(block)
    return RecordInput(
        **_common_record_fields(data_point),
        startDate=start,
        endDate=end,
        type=HK_FLIGHTS_CLIMBED,
        value=str(block.get("floorsClimbed", "0")),
        unit="count",
    )


def map_active_zone_minutes(data_point: dict[str, Any]) -> RecordInput:
    """Active-zone minutes over an Interval."""
    block = data_point["activeZoneMinutes"]
    start, end = _interval_bounds(block)
    return RecordInput(
        **_common_record_fields(data_point),
        startDate=start,
        endDate=end,
        type=HK_ACTIVE_ZONE_MINUTES,
        value=str(block.get("minutes", "0")),
        unit="min",
    )


def map_daily_resting_heart_rate(data_point: dict[str, Any]) -> RecordInput:
    """One daily-aggregate resting heart rate."""
    block = data_point["dailyRestingHeartRate"]
    start, end = _interval_bounds(block)
    return RecordInput(
        **_common_record_fields(data_point),
        startDate=start,
        endDate=end,
        type=HK_RESTING_HEART_RATE,
        value=str(block.get("beatsPerMinute", "0")),
        unit="count/min",
    )


def map_daily_oxygen_saturation(data_point: dict[str, Any]) -> RecordInput:
    """Daily-aggregate SpO2 average (percentage)."""
    block = data_point["dailyOxygenSaturation"]
    start, end = _interval_bounds(block)
    return RecordInput(
        **_common_record_fields(data_point),
        startDate=start,
        endDate=end,
        type=HK_OXYGEN_SATURATION,
        value=str(block.get("averagePercentage") or block.get("percentage") or "0"),
        unit="%",
    )


def map_body_fat(data_point: dict[str, Any]) -> RecordInput:
    """Body-fat percentage Sample (point in time)."""
    block = data_point["bodyFat"]
    instant = _sample_instant(block)
    return RecordInput(
        **_common_record_fields(data_point),
        startDate=instant,
        endDate=instant,
        type=HK_BODY_FAT_PERCENTAGE,
        value=str(block.get("percentage", "0")),
        unit="%",
    )


def map_height(data_point: dict[str, Any]) -> RecordInput:
    """Height Sample (point in time). Live payload reports millimeters."""
    block = data_point["height"]
    instant = _sample_instant(block)
    # Live payload: heightMillimeters as string. Older drafts assumed heightMeters/heightM.
    if "heightMillimeters" in block:
        height_m = float(block["heightMillimeters"]) / 1000.0
    else:
        height_m = float(block.get("heightMeters") or block.get("heightM") or 0)
    return RecordInput(
        **_common_record_fields(data_point),
        startDate=instant,
        endDate=instant,
        type=HK_HEIGHT,
        value=str(height_m),
        unit="m",
    )


def map_sleep_session(data_point: dict[str, Any]) -> list[RecordInput]:
    """Decompose a Google sleep session into one Record per stage interval.

    Live payload puts stage bounds on the stage object directly
    (``stages[].startTime`` / ``stages[].endTime``); earlier guesses assumed a
    nested ``interval`` block. We accept both. Stage label is ``stages[].type``.
    """
    block = data_point["sleep"]
    common = _common_record_fields(data_point)
    records: list[RecordInput] = []
    for stage in block.get("stages") or []:
        # Accept either flat (live) or nested (earlier-guessed) time shape.
        if "startTime" in stage and "endTime" in stage:
            start = _parse_dt(stage["startTime"])
            end = _parse_dt(stage["endTime"])
        else:
            start, end = _interval_bounds(stage)
        label = stage.get("type") or stage.get("stage", "")
        mapped = _SLEEP_STAGE_MAP.get(str(label).upper())
        if mapped is None:
            continue
        records.append(
            RecordInput(
                **common,
                startDate=start,
                endDate=end,
                type=SLEEP_TYPE,
                value=mapped,
            )
        )
    return records


def map_exercise(data_point: dict[str, Any]) -> WorkoutInput:
    block = data_point["exercise"]
    start, end = _interval_bounds(block)
    metrics = block.get("metricsSummary") or {}
    duration_seconds = (end - start).total_seconds()
    distance_mm = metrics.get("distanceMillimeters") or metrics.get(
        "distanceMillimiters"
    )
    distance_value: float | None = None
    if distance_mm is not None:
        distance_value = float(distance_mm) / 1_000_000.0  # mm → km

    extra_metadata: list[MetadataEntry] = []
    if "steps" in metrics:
        extra_metadata.append(MetadataEntry(key="steps", value=str(metrics["steps"])))
    if "averageHeartRateBeatsPerMinute" in metrics:
        extra_metadata.append(
            MetadataEntry(
                key="average_heart_rate_bpm",
                value=str(metrics["averageHeartRateBeatsPerMinute"]),
            )
        )

    return WorkoutInput(
        recordId=_record_id(data_point),
        startDate=start,
        endDate=end,
        creationDate=_parse_dt(block.get("updateTime")),
        sourceName=SOURCE_NAME,
        durationUnit="s",
        duration=duration_seconds,
        workoutActivityType=str(block.get("exerciseType", "UNKNOWN")),
        caloriesBurned=float(metrics["caloriesKcal"])
        if "caloriesKcal" in metrics
        else None,
        caloriesUnit="kcal" if "caloriesKcal" in metrics else None,
        distance=distance_value,
        distanceUnit="km" if distance_value is not None else None,
        metadataEntry=extra_metadata or None,
    )


# Orchestrator ----------------------------------------------------------------


_RECORD_MAPPERS: dict[str, Callable[[dict[str, Any]], list[RecordInput]]] = {
    DATA_TYPE_STEPS: lambda dp: [map_steps(dp)],
    DATA_TYPE_TOTAL_CALORIES: lambda dp: [map_total_calories(dp)],
    DATA_TYPE_HEART_RATE: lambda dp: [map_heart_rate(dp)],
    DATA_TYPE_WEIGHT: lambda dp: [map_weight(dp)],
    DATA_TYPE_SLEEP: map_sleep_session,
    DATA_TYPE_DISTANCE: lambda dp: [map_distance(dp)],
    DATA_TYPE_ALTITUDE: lambda dp: [map_altitude(dp)],
    DATA_TYPE_FLOORS: lambda dp: [map_floors(dp)],
    DATA_TYPE_ACTIVE_ZONE_MINUTES: lambda dp: [map_active_zone_minutes(dp)],
    DATA_TYPE_DAILY_RESTING_HEART_RATE: lambda dp: [map_daily_resting_heart_rate(dp)],
    DATA_TYPE_DAILY_OXYGEN_SATURATION: lambda dp: [map_daily_oxygen_saturation(dp)],
    DATA_TYPE_BODY_FAT: lambda dp: [map_body_fat(dp)],
    DATA_TYPE_HEIGHT: lambda dp: [map_height(dp)],
}

# Google rejects ``list`` for these — only rollUp / dailyRollUp / reconcile work.
# They're absent from DEFAULT_DATA_TYPES (so the default native-resolution sync
# skips them) but become available when the caller passes
# ``resolution_minutes=N`` to :func:`sync_user`.
ROLLUP_ONLY_DATA_TYPES: tuple[str, ...] = (
    DATA_TYPE_TOTAL_CALORIES,
    DATA_TYPE_FLOORS,
)

# Types that don't support the rollUp endpoint at all (Sessions, point-in-time
# Samples without an aggregation, pre-aggregated Daily summaries). When a
# resolution is requested, these fall back to the native ``list`` endpoint.
_ROLLUP_UNSUPPORTED_DATA_TYPES = frozenset(
    {
        DATA_TYPE_SLEEP,
        DATA_TYPE_EXERCISE,
        DATA_TYPE_HEIGHT,
        DATA_TYPE_DAILY_RESTING_HEART_RATE,
        DATA_TYPE_DAILY_OXYGEN_SATURATION,
    }
)


def _rollup_value(
    point: dict[str, Any], data_type: str
) -> tuple[str, str | None] | None:
    """Pull the aggregated value + unit from a rollupDataPoint for ``data_type``.

    Returns ``(value, unit)`` or ``None`` if the point has no value for this type.
    Field names are taken from the v4 discovery doc's ``*RollupValue`` schemas.
    """
    key = data_type.replace("-", "")  # rollup payload uses camelCase keys
    # Map kebab-case data type → camelCase block name in the response.
    block_key = {
        DATA_TYPE_STEPS: "steps",
        DATA_TYPE_DISTANCE: "distance",
        DATA_TYPE_HEART_RATE: "heartRate",
        DATA_TYPE_WEIGHT: "weight",
        DATA_TYPE_BODY_FAT: "bodyFat",
        DATA_TYPE_ALTITUDE: "altitude",
        DATA_TYPE_TOTAL_CALORIES: "totalCalories",
        DATA_TYPE_FLOORS: "floors",
        DATA_TYPE_ACTIVE_ZONE_MINUTES: "activeZoneMinutes",
    }.get(data_type, key)
    block = point.get(block_key)
    if not isinstance(block, dict):
        return None
    if data_type == DATA_TYPE_STEPS and "countSum" in block:
        return str(block["countSum"]), "count"
    if data_type == DATA_TYPE_FLOORS and "countSum" in block:
        return str(block["countSum"]), "count"
    if data_type == DATA_TYPE_DISTANCE and "millimetersSum" in block:
        return str(float(block["millimetersSum"]) / 1000.0), "m"
    if data_type == DATA_TYPE_ALTITUDE and "gainMillimetersSum" in block:
        return str(float(block["gainMillimetersSum"]) / 1000.0), "m"
    if data_type == DATA_TYPE_HEART_RATE and "beatsPerMinuteAvg" in block:
        return str(block["beatsPerMinuteAvg"]), "count/min"
    if data_type == DATA_TYPE_WEIGHT and "weightGramsAvg" in block:
        return str(float(block["weightGramsAvg"]) / 1000.0), "kg"
    if data_type == DATA_TYPE_BODY_FAT and "bodyFatPercentageAvg" in block:
        return str(block["bodyFatPercentageAvg"]), "%"
    if data_type == DATA_TYPE_TOTAL_CALORIES and "kcalSum" in block:
        return str(block["kcalSum"]), "kcal"
    if data_type == DATA_TYPE_ACTIVE_ZONE_MINUTES:
        # Sum across all heart-rate zones for a single "active zone minutes" value.
        total = 0
        for field in (
            "sumInFatBurnHeartZone",
            "sumInCardioHeartZone",
            "sumInPeakHeartZone",
        ):
            if field in block:
                total += int(block[field])
        return str(total), "min"
    return None


def _rollup_to_record(data_type: str, point: dict[str, Any]) -> RecordInput | None:
    """Convert one ``rollupDataPoint`` to a :class:`RecordInput`."""
    valued = _rollup_value(point, data_type)
    if valued is None:
        return None
    value, unit = valued
    start = _parse_dt(point["startTime"])
    end = _parse_dt(point["endTime"])

    # Map to the same HK identifier the native (list-path) mapper uses, so
    # downstream queries see one consistent type per metric.
    record_type = {
        DATA_TYPE_STEPS: str(ActivityMetric.STEPS),
        DATA_TYPE_DISTANCE: HK_DISTANCE_WALKING_RUNNING,
        DATA_TYPE_HEART_RATE: HK_HEART_RATE,
        DATA_TYPE_WEIGHT: HK_BODY_MASS,
        DATA_TYPE_BODY_FAT: HK_BODY_FAT_PERCENTAGE,
        DATA_TYPE_ALTITUDE: HK_ALTITUDE_GAIN,
        DATA_TYPE_TOTAL_CALORIES: str(ActivityMetric.ACTIVE_CALORIES),
        DATA_TYPE_FLOORS: HK_FLIGHTS_CLIMBED,
        DATA_TYPE_ACTIVE_ZONE_MINUTES: HK_ACTIVE_ZONE_MINUTES,
    }[data_type]

    return RecordInput(
        recordId=None,
        startDate=start,
        endDate=end,
        creationDate=start,
        sourceName=SOURCE_NAME,
        type=record_type,
        value=value,
        unit=unit,
    )


DEFAULT_DATA_TYPES: tuple[str, ...] = (
    DATA_TYPE_STEPS,
    DATA_TYPE_HEART_RATE,
    DATA_TYPE_WEIGHT,
    DATA_TYPE_HEIGHT,
    DATA_TYPE_SLEEP,
    DATA_TYPE_EXERCISE,
    DATA_TYPE_DISTANCE,
    DATA_TYPE_ALTITUDE,
    DATA_TYPE_ACTIVE_ZONE_MINUTES,
    DATA_TYPE_DAILY_RESTING_HEART_RATE,
    DATA_TYPE_DAILY_OXYGEN_SATURATION,
    DATA_TYPE_BODY_FAT,
)


def _civil(ts: datetime) -> str:
    """Format ``ts`` as the civil-time string Google's filter language expects.

    No timezone, no microseconds — matches the codelab pattern
    ``"2026-02-22T00:00:00"``.
    """
    return (
        ts.astimezone(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")
    )


# Data types we fetch unfiltered — server rejects every filter syntax we've
# tried. Empirically confirmed against a live account on 2026-05-15:
#   * Sample types (heart-rate, weight, height, body-fat): no documented
#     filter field; payload uses ``sampleTime``, not ``interval``.
#   * Sleep (Session): filters on ``interval.civil_start_time`` / ``start_time``
#     / ``civil_start_time`` all returned INVALID_DATA_POINT_FILTER_DATA_TYPE_MEMBER.
#   * Daily aggregates (daily-resting-heart-rate, daily-oxygen-saturation): same.
# Pagination + recency ordering bound the result for these.
_UNFILTERABLE_DATA_TYPES = frozenset(
    {
        DATA_TYPE_HEART_RATE,
        DATA_TYPE_WEIGHT,
        DATA_TYPE_BODY_FAT,
        DATA_TYPE_HEIGHT,
        DATA_TYPE_SLEEP,
        DATA_TYPE_DAILY_RESTING_HEART_RATE,
        DATA_TYPE_DAILY_OXYGEN_SATURATION,
    }
)


def _build_filter(data_type: str, start: datetime, end: datetime) -> str | None:
    """Return the ``filter`` query-string value for a given data type, or ``None``
    to fetch unfiltered.

    Interval/Session/Daily types: one-sided ``<key>.interval.civil_start_time >=``
    bound. Google's filter language rejects ``civil_end_time``/``end_time`` as
    filterable fields (verified empirically against ``steps`` — combined AND
    queries return ``INVALID_DATA_POINT_FILTER_DATA_TYPE_MEMBER``). Upper bound
    is enforced client-side in ``sync_user``.

    Sample types: no filter — REST docs don't specify a filter field for
    samples, so we fetch and rely on pagination + recency ordering.
    """
    if data_type in _UNFILTERABLE_DATA_TYPES:
        return None
    key = data_type.replace("-", "_")
    return f'{key}.interval.civil_start_time >= "{_civil(start)}"'


# Basal calories --------------------------------------------------------------


_BASAL_RESULT_KEY = "basal-calories"


def _profile_dob_and_gender(profile: dict[str, Any]) -> tuple[datetime | None, str]:
    """Best-effort extraction of DOB + gender from Google Health profile payload.

    Google's profile schema isn't fully documented; we try the most common
    spellings. Returns ``(None, "")`` when either field can't be resolved —
    callers fall back to the median-table BMR via :func:`get_bmr`.
    """
    dob_raw = (
        profile.get("dateOfBirth")
        or profile.get("birthday")
        or profile.get("birthDate")
    )
    dob: datetime | None = None
    if isinstance(dob_raw, str):
        try:
            dob = dateutil.parser.parse(dob_raw)
        except (ValueError, TypeError):
            dob = None
    elif isinstance(dob_raw, dict):
        # Google sometimes uses civil-date {"year": ..., "month": ..., "day": ...}.
        try:
            dob = datetime(
                int(dob_raw["year"]), int(dob_raw["month"]), int(dob_raw["day"])
            )
        except (KeyError, TypeError, ValueError):
            dob = None

    gender_raw = str(profile.get("gender") or profile.get("sex") or "").upper()
    if gender_raw.startswith("M"):
        gender = "M"
    elif gender_raw.startswith("F"):
        gender = "F"
    else:
        gender = ""

    return dob, gender


def _latest_value_at_or_before(customer: Any, hk_type: str, day: date) -> float | None:
    cutoff = datetime.combine(
        day + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc
    )
    record = (
        Record.objects.filter(customer=customer, type=hk_type, startDate__lt=cutoff)
        .order_by("-startDate")
        .first()
    )
    if record is None:
        return None
    try:
        return float(record.value)
    except (TypeError, ValueError):
        return None


def compute_basal_calories(
    connection: GoogleHealthConnection,
    *,
    start: datetime,
    end: datetime,
    profile: dict[str, Any] | None = None,
    client: GoogleHealthClient | None = None,
    admin_create_date: datetime | None = None,
) -> int:
    """Estimate daily BMR for every day in [start, end] and persist as
    ``ActivityMetric.BASAL_CALORIES`` records.

    Uses Mifflin-St Jeor (:func:`healthdatamodel.bmr.calculate_bmr`) when
    height + weight are both available on or before each day, falling back to
    the median-table lookup (:func:`healthdatamodel.bmr.get_bmr`) when either
    is missing.

    Pass ``profile`` to skip the HTTP call (handy in tests). If both
    ``profile`` and ``client`` are ``None``, a transient ``GoogleHealthClient``
    is built for the profile fetch only.
    """
    owns_client = False
    if profile is None:
        owns_client = client is None
        if client is None:
            client = GoogleHealthClient(connection)
        try:
            profile = client.get_profile()
        finally:
            if owns_client:
                client.close()

    dob, gender = _profile_dob_and_gender(profile or {})
    age = age_from_dob(dob.date()) if dob is not None else None

    customer = connection.customer
    creation = admin_create_date or datetime.now(timezone.utc)
    records: list[RecordInput] = []
    day = start.date()
    end_day = end.date()
    while day <= end_day:
        weight = _latest_value_at_or_before(customer, HK_BODY_MASS, day)
        height_m = _latest_value_at_or_before(customer, HK_HEIGHT, day)

        if weight is not None and height_m is not None and age is not None and gender:
            bmr = calculate_bmr(age, gender, weight, height_m * 100.0)
        else:
            bmr = get_bmr(age=age, gender=gender)

        day_start = datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc)
        day_end = day_start + timedelta(days=1)
        records.append(
            RecordInput(
                recordId=f"basal-{day.isoformat()}",
                startDate=day_start,
                endDate=day_end,
                creationDate=creation,
                sourceName=SOURCE_NAME,
                type=str(ActivityMetric.BASAL_CALORIES),
                value=str(bmr),
                unit="kcal",
            )
        )
        day += timedelta(days=1)

    ingest_records(customer, records, source=DataSource.GOOGLE_HEALTH)
    return len(records)


def sync_user(
    connection: GoogleHealthConnection,
    *,
    start: datetime,
    end: datetime,
    data_types: list[str] | None = None,
    resolution_minutes: int | None = None,
    client: GoogleHealthClient | None = None,
    compute_basal: bool = True,
) -> SyncResult:
    """Fetch + ingest all configured data types for ``connection`` over [start, end].

    Pass a pre-built ``client`` to override the default (useful in tests).
    With ``compute_basal=True`` (default), runs :func:`compute_basal_calories`
    after the main ingest so a daily ``BASAL_CALORIES`` series is available
    for downstream MET calculations.

    ``resolution_minutes`` switches the ingest path:

    * ``None`` (default) — native granularity via the ``list`` endpoint. Each
      Google data point becomes one Record. Sleep stages decompose into
      per-stage records; exercise → Workout.

    * positive int — aggregate via the ``rollUp`` endpoint with
      ``windowSize={N*60}s`` (so ``1440`` gives one record per day). Each
      rollup window becomes one Record. Data types that don't support
      rollUp (sleep, exercise, height, daily-*) fall back to native.

    With a resolution set, ``total-calories`` and ``floors`` become usable
    (the ``list`` endpoint rejects them; ``rollUp`` is their only option).
    """
    if resolution_minutes is not None and resolution_minutes <= 0:
        raise ValueError("resolution_minutes must be positive or None")

    result = SyncResult()
    owns_client = client is None
    if client is None:
        client = GoogleHealthClient(connection)

    requested = list(data_types or DEFAULT_DATA_TYPES)
    if resolution_minutes is not None:
        # Expand the default set with rollup-only types when a resolution is set.
        if data_types is None:
            for dt in ROLLUP_ONLY_DATA_TYPES:
                if dt not in requested:
                    requested.append(dt)

    try:
        for data_type in requested:
            use_rollup = (
                resolution_minutes is not None
                and data_type not in _ROLLUP_UNSUPPORTED_DATA_TYPES
            )

            if use_rollup:
                window_seconds = resolution_minutes * 60
                rollup_points = list(
                    client.iter_roll_up(
                        data_type,
                        start=start,
                        end=end,
                        window_seconds=window_seconds,
                    )
                )
                records = [
                    rec
                    for rec in (_rollup_to_record(data_type, p) for p in rollup_points)
                    if rec is not None
                ]
                ingest_records(
                    connection.customer, records, source=DataSource.GOOGLE_HEALTH
                )
                result.counts[data_type] = len(records)
                continue

            filter_expr = _build_filter(data_type, start, end)
            data_points = list(client.iter_data_points(data_type, filter=filter_expr))

            if data_type == DATA_TYPE_EXERCISE:
                workouts = [map_exercise(dp) for dp in data_points]
                ingest_workouts(
                    connection.customer, workouts, source=DataSource.GOOGLE_HEALTH
                )
                result.counts[data_type] = len(workouts)
                continue

            mapper = _RECORD_MAPPERS.get(data_type)
            if mapper is None:
                continue
            records: list[RecordInput] = []
            for dp in data_points:
                records.extend(mapper(dp))
            ingest_records(
                connection.customer, records, source=DataSource.GOOGLE_HEALTH
            )
            result.counts[data_type] = len(records)

        if compute_basal:
            # Computed AFTER the main loop so the latest weight/height records
            # this sync brought in are picked up by _latest_value_at_or_before.
            basal_count = compute_basal_calories(
                connection, start=start, end=end, client=client
            )
            result.counts[_BASAL_RESULT_KEY] = basal_count
    finally:
        if owns_client:
            client.close()

    connection.last_sync_at = datetime.now(timezone.utc)
    connection.save(update_fields=["last_sync_at"])
    result.finished_at = datetime.now(timezone.utc)
    return result
