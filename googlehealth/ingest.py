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
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Callable

from healthdatamodel.constants import DataSource
from healthdatamodel.ingest import ingest_records, ingest_workouts
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

# Map Google's sleep stage strings → healthdatamodel SleepValue.
_SLEEP_STAGE_MAP: dict[str, str] = {
    "LIGHT": SleepValue.ASLEEP_CORE,
    "DEEP": SleepValue.ASLEEP_DEEP,
    "REM": SleepValue.ASLEEP_REM,
    "AWAKE": SleepValue.AWAKE,
    "IN_BED": SleepValue.IN_BED,
    "UNSPECIFIED": SleepValue.ASLEEP_UNSPECIFIED,
    "OUT_OF_BED": SleepValue.AWAKE,
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
        "creationDate": _parse_dt(_update_time(data_point)),
        "sourceName": SOURCE_NAME,
    }


def _update_time(data_point: dict[str, Any]) -> str | None:
    # The update_time lives nested under the type block, e.g. data_point["exercise"]["updateTime"].
    for block in data_point.values():
        if isinstance(block, dict) and "updateTime" in block:
            return block["updateTime"]
    return None


# Mappers ---------------------------------------------------------------------


def map_steps(data_point: dict[str, Any]) -> RecordInput:
    block = data_point["steps"]
    start, end = _interval_bounds(block)
    return RecordInput(
        **_common_record_fields(data_point),
        startDate=start,
        endDate=end,
        type=str(ActivityMetric.STEPS),
        value=str(block.get("stepCount", "0")),
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
    # Heart-rate is a Sample (point-in-time). Use the same instant for start and end.
    instant = _parse_dt(block.get("time"))
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
    instant = _parse_dt(block.get("time"))
    return RecordInput(
        **_common_record_fields(data_point),
        startDate=instant,
        endDate=instant,
        type=HK_BODY_MASS,
        value=str(block.get("weightKg", "0")),
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
    instant = _parse_dt(block.get("time"))
    return RecordInput(
        **_common_record_fields(data_point),
        startDate=instant,
        endDate=instant,
        type=HK_BODY_FAT_PERCENTAGE,
        value=str(block.get("percentage", "0")),
        unit="%",
    )


def map_sleep_session(data_point: dict[str, Any]) -> list[RecordInput]:
    """Decompose a Google sleep session into one Record per stage interval."""
    block = data_point["sleep"]
    common = _common_record_fields(data_point)
    records: list[RecordInput] = []
    for stage in block.get("stages") or []:
        start, end = _interval_bounds(stage)
        mapped = _SLEEP_STAGE_MAP.get(str(stage.get("stage", "")).upper())
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
}

DEFAULT_DATA_TYPES: tuple[str, ...] = (
    DATA_TYPE_STEPS,
    DATA_TYPE_TOTAL_CALORIES,
    DATA_TYPE_HEART_RATE,
    DATA_TYPE_WEIGHT,
    DATA_TYPE_SLEEP,
    DATA_TYPE_EXERCISE,
    DATA_TYPE_DISTANCE,
    DATA_TYPE_ALTITUDE,
    DATA_TYPE_FLOORS,
    DATA_TYPE_ACTIVE_ZONE_MINUTES,
    DATA_TYPE_DAILY_RESTING_HEART_RATE,
    DATA_TYPE_DAILY_OXYGEN_SATURATION,
    DATA_TYPE_BODY_FAT,
)


def _interval_filter(google_filter_key: str, start: datetime, end: datetime) -> str:
    return (
        f'{google_filter_key}.interval.start_time >= "{start.isoformat()}" '
        f'AND {google_filter_key}.interval.end_time <= "{end.isoformat()}"'
    )


def sync_user(
    connection: GoogleHealthConnection,
    *,
    start: datetime,
    end: datetime,
    data_types: list[str] | None = None,
    client: GoogleHealthClient | None = None,
) -> SyncResult:
    """Fetch + ingest all configured data types for ``connection`` over [start, end].

    Pass a pre-built ``client`` to override the default (useful in tests).
    """
    result = SyncResult()
    owns_client = client is None
    if client is None:
        client = GoogleHealthClient(connection)

    try:
        for data_type in data_types or DEFAULT_DATA_TYPES:
            filter_key = data_type.replace("-", "_")
            filter_expr = _interval_filter(filter_key, start, end)
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
    finally:
        if owns_client:
            client.close()

    connection.last_sync_at = datetime.now(timezone.utc)
    connection.save(update_fields=["last_sync_at"])
    result.finished_at = datetime.now(timezone.utc)
    return result
