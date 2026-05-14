"""Tests for googlehealth.ingest — mappers + sync_user orchestration."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import pytest
import respx
import responses
from healthdatamodel.models import Record, Workout, WorkoutMetadataEntry
from healthdatamodel.query import SLEEP_TYPE, ActivityMetric, SleepValue
from httpx import Response

from googlehealth import ingest, oauth
from googlehealth.client import GoogleHealthClient
from googlehealth.constants import (
    API_BASE_URL,
    API_VERSION,
    DATA_SOURCE,
    DATA_TYPE_EXERCISE,
    DATA_TYPE_HEART_RATE,
    DATA_TYPE_SLEEP,
    DATA_TYPE_STEPS,
    DATA_TYPE_TOTAL_CALORIES,
    DATA_TYPE_WEIGHT,
    OAUTH_TOKEN_URL,
    SCOPE_ACTIVITY_AND_FITNESS_READONLY,
    SOURCE_NAME,
)
from googlehealth.models import GoogleHealthConnection


def _dp_url(data_type: str) -> str:
    return f"{API_BASE_URL}/{API_VERSION}/users/me/dataTypes/{data_type}/dataPoints"


# Pure mapper tests ----------------------------------------------------------


def test_map_steps():
    dp = {
        "name": "users/123/dataTypes/steps/dataPoints/p1",
        "steps": {
            "interval": {
                "startTime": "2026-05-01T10:00:00Z",
                "endTime": "2026-05-01T10:15:00Z",
            },
            "stepCount": "1234",
            "updateTime": "2026-05-01T10:20:00Z",
        },
    }
    rec = ingest.map_steps(dp)
    assert rec.recordId == "p1"
    assert rec.type == str(ActivityMetric.STEPS)
    assert rec.value == "1234"
    assert rec.unit == "count"
    assert rec.sourceName == SOURCE_NAME
    assert rec.startDate == datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc)
    assert rec.endDate == datetime(2026, 5, 1, 10, 15, tzinfo=timezone.utc)


def test_map_total_calories_uses_active_calories_type():
    dp = {
        "name": "users/x/dataTypes/total-calories/dataPoints/c1",
        "totalCalories": {
            "interval": {
                "startTime": "2026-05-01T10:00:00Z",
                "endTime": "2026-05-01T10:15:00Z",
            },
            "caloriesKcal": 42.5,
            "updateTime": "2026-05-01T10:20:00Z",
        },
    }
    rec = ingest.map_total_calories(dp)
    assert rec.type == str(ActivityMetric.ACTIVE_CALORIES)
    assert rec.value == "42.5"
    assert rec.unit == "kcal"


def test_map_heart_rate_point_in_time():
    dp = {
        "name": "users/x/dataTypes/heart-rate/dataPoints/h1",
        "heartRate": {
            "time": "2026-05-01T10:00:00Z",
            "beatsPerMinute": 72,
            "updateTime": "2026-05-01T10:00:01Z",
        },
    }
    rec = ingest.map_heart_rate(dp)
    assert rec.type == ingest.HK_HEART_RATE
    assert rec.value == "72"
    assert rec.startDate == rec.endDate


def test_map_weight():
    dp = {
        "name": "users/x/dataTypes/weight/dataPoints/w1",
        "weight": {
            "time": "2026-05-01T08:00:00Z",
            "weightKg": 75.4,
            "updateTime": "2026-05-01T08:00:01Z",
        },
    }
    rec = ingest.map_weight(dp)
    assert rec.type == ingest.HK_BODY_MASS
    assert rec.value == "75.4"
    assert rec.unit == "kg"


def test_map_sleep_session_decomposes_stages():
    dp = {
        "name": "users/x/dataTypes/sleep/dataPoints/s1",
        "sleep": {
            "interval": {
                "startTime": "2026-05-01T03:00:00Z",
                "endTime": "2026-05-01T07:00:00Z",
            },
            "stages": [
                {
                    "interval": {
                        "startTime": "2026-05-01T03:00:00Z",
                        "endTime": "2026-05-01T04:00:00Z",
                    },
                    "stage": "LIGHT",
                },
                {
                    "interval": {
                        "startTime": "2026-05-01T04:00:00Z",
                        "endTime": "2026-05-01T05:30:00Z",
                    },
                    "stage": "DEEP",
                },
                {
                    "interval": {
                        "startTime": "2026-05-01T05:30:00Z",
                        "endTime": "2026-05-01T06:30:00Z",
                    },
                    "stage": "REM",
                },
                {
                    "interval": {
                        "startTime": "2026-05-01T06:30:00Z",
                        "endTime": "2026-05-01T07:00:00Z",
                    },
                    "stage": "AWAKE",
                },
                {
                    "interval": {
                        "startTime": "2026-05-01T07:00:00Z",
                        "endTime": "2026-05-01T07:01:00Z",
                    },
                    "stage": "WEIRD_NEW_STAGE",  # unknown stages are skipped
                },
            ],
            "updateTime": "2026-05-01T07:05:00Z",
        },
    }
    records = ingest.map_sleep_session(dp)
    assert len(records) == 4
    assert [r.value for r in records] == [
        SleepValue.ASLEEP_CORE,
        SleepValue.ASLEEP_DEEP,
        SleepValue.ASLEEP_REM,
        SleepValue.AWAKE,
    ]
    assert all(r.type == SLEEP_TYPE for r in records)


def test_map_exercise():
    dp = {
        "name": "users/x/dataTypes/exercise/dataPoints/e1",
        "dataSource": {"recordingMethod": "MANUAL", "platform": "FITBIT"},
        "exercise": {
            "interval": {
                "startTime": "2026-02-23T13:10:00Z",
                "endTime": "2026-02-23T13:25:00Z",
            },
            "exerciseType": "WALKING",
            "metricsSummary": {
                "caloriesKcal": 16,
                "distanceMillimeters": 1609344,
                "steps": "2038",
                "averageHeartRateBeatsPerMinute": "81",
            },
            "displayName": "Walk",
            "updateTime": "2026-02-24T01:19:22.450466Z",
        },
    }
    workout = ingest.map_exercise(dp)
    assert workout.recordId == "e1"
    assert workout.workoutActivityType == "WALKING"
    assert workout.duration == 15 * 60  # 15-minute walk
    assert workout.caloriesBurned == 16.0
    assert workout.distance is not None
    assert abs(workout.distance - 1.609344) < 1e-6
    assert workout.distanceUnit == "km"
    keys = {entry.key for entry in workout.metadataEntry or []}
    assert {"steps", "average_heart_rate_bpm"} <= keys


# sync_user integration ------------------------------------------------------


def _page(data_points: list[dict]) -> dict:
    return {"dataPoints": data_points, "nextPageToken": ""}


@respx.mock
def test_sync_user_persists_each_data_type(connection, customer):
    steps_dp = {
        "name": "users/me/dataTypes/steps/dataPoints/sp1",
        "steps": {
            "interval": {
                "startTime": "2026-05-01T10:00:00Z",
                "endTime": "2026-05-01T10:15:00Z",
            },
            "stepCount": "500",
            "updateTime": "2026-05-01T10:16:00Z",
        },
    }
    calories_dp = {
        "name": "users/me/dataTypes/total-calories/dataPoints/c1",
        "totalCalories": {
            "interval": {
                "startTime": "2026-05-01T10:00:00Z",
                "endTime": "2026-05-01T10:15:00Z",
            },
            "caloriesKcal": 35,
            "updateTime": "2026-05-01T10:16:00Z",
        },
    }
    hr_dp = {
        "name": "users/me/dataTypes/heart-rate/dataPoints/hr1",
        "heartRate": {
            "time": "2026-05-01T10:05:00Z",
            "beatsPerMinute": 80,
            "updateTime": "2026-05-01T10:05:01Z",
        },
    }
    weight_dp = {
        "name": "users/me/dataTypes/weight/dataPoints/w1",
        "weight": {
            "time": "2026-05-01T08:00:00Z",
            "weightKg": 70.0,
            "updateTime": "2026-05-01T08:00:01Z",
        },
    }
    sleep_dp = {
        "name": "users/me/dataTypes/sleep/dataPoints/s1",
        "sleep": {
            "interval": {
                "startTime": "2026-05-01T03:00:00Z",
                "endTime": "2026-05-01T07:00:00Z",
            },
            "stages": [
                {
                    "interval": {
                        "startTime": "2026-05-01T03:00:00Z",
                        "endTime": "2026-05-01T04:00:00Z",
                    },
                    "stage": "LIGHT",
                },
                {
                    "interval": {
                        "startTime": "2026-05-01T04:00:00Z",
                        "endTime": "2026-05-01T05:00:00Z",
                    },
                    "stage": "DEEP",
                },
            ],
            "updateTime": "2026-05-01T07:01:00Z",
        },
    }
    exercise_dp = {
        "name": "users/me/dataTypes/exercise/dataPoints/e1",
        "exercise": {
            "interval": {
                "startTime": "2026-05-01T17:00:00Z",
                "endTime": "2026-05-01T17:30:00Z",
            },
            "exerciseType": "RUNNING",
            "metricsSummary": {"caloriesKcal": 200, "distanceMillimeters": 5_000_000},
            "updateTime": "2026-05-01T17:30:01Z",
        },
    }

    for data_type, dp in [
        (DATA_TYPE_STEPS, steps_dp),
        (DATA_TYPE_TOTAL_CALORIES, calories_dp),
        (DATA_TYPE_HEART_RATE, hr_dp),
        (DATA_TYPE_WEIGHT, weight_dp),
        (DATA_TYPE_SLEEP, sleep_dp),
        (DATA_TYPE_EXERCISE, exercise_dp),
    ]:
        respx.get(_dp_url(data_type)).mock(return_value=Response(200, json=_page([dp])))

    start = datetime(2026, 5, 1, tzinfo=timezone.utc)
    end = datetime(2026, 5, 2, tzinfo=timezone.utc)

    result = ingest.sync_user(connection, start=start, end=end)

    # Per-type counts
    assert result.counts[DATA_TYPE_STEPS] == 1
    assert result.counts[DATA_TYPE_TOTAL_CALORIES] == 1
    assert result.counts[DATA_TYPE_HEART_RATE] == 1
    assert result.counts[DATA_TYPE_WEIGHT] == 1
    assert result.counts[DATA_TYPE_SLEEP] == 2  # two stages
    assert result.counts[DATA_TYPE_EXERCISE] == 1
    assert result.total == 7

    # Records landed in healthdatamodel
    records = Record.objects.filter(customer=customer)
    assert records.count() == 6  # 4 samples + 2 sleep stage records
    assert {r.source for r in records} == {DATA_SOURCE}
    assert {r.sourceName for r in records} == {SOURCE_NAME}

    # Workout landed via ORM stopgap, with calories + distance in metadata
    workout = Workout.objects.get(customer=customer)
    assert workout.workoutActivityType == "RUNNING"
    assert workout.duration == 1800
    metadata_keys = set(
        WorkoutMetadataEntry.objects.filter(workout=workout).values_list(
            "key", flat=True
        )
    )
    assert {"caloriesBurned", "distance_km"} <= metadata_keys

    # Connection got a sync timestamp
    connection.refresh_from_db()
    assert connection.last_sync_at is not None


@respx.mock
def test_sync_user_respects_data_types_argument(connection):
    respx.get(_dp_url(DATA_TYPE_STEPS)).mock(return_value=Response(200, json=_page([])))

    result = ingest.sync_user(
        connection,
        start=datetime(2026, 5, 1, tzinfo=timezone.utc),
        end=datetime(2026, 5, 2, tzinfo=timezone.utc),
        data_types=[DATA_TYPE_STEPS],
    )

    assert list(result.counts.keys()) == [DATA_TYPE_STEPS]


@respx.mock
@responses.activate
def test_sync_user_handles_expired_token(customer):
    """End-to-end: stale token → proactive refresh → ingest flow continues."""
    responses.add(
        responses.POST,
        OAUTH_TOKEN_URL,
        json={
            "access_token": "ya29.fresh",
            "expires_in": 3600,
            "token_type": "Bearer",
            "scope": SCOPE_ACTIVITY_AND_FITNESS_READONLY,
        },
    )
    conn = GoogleHealthConnection.objects.create(
        customer=customer,
        google_user_id="g1",
        access_token="ya29.stale",
        refresh_token="1//refresh",
        token_expires_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        scopes=[SCOPE_ACTIVITY_AND_FITNESS_READONLY],
    )
    respx.get(_dp_url(DATA_TYPE_STEPS)).mock(return_value=Response(200, json=_page([])))

    ingest.sync_user(
        conn,
        start=datetime(2026, 5, 1, tzinfo=timezone.utc),
        end=datetime(2026, 5, 2, tzinfo=timezone.utc),
        data_types=[DATA_TYPE_STEPS],
    )

    conn.refresh_from_db()
    assert conn.access_token == "ya29.fresh"


@pytest.mark.live
def test_sync_user_against_real_api(db):
    """Sync the last 24h for the test refresh token. Self-skips without env vars."""
    refresh_token = os.getenv("GOOGLE_HEALTH_TEST_REFRESH_TOKEN")
    client_id = os.getenv("GOOGLE_HEALTH_TEST_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_HEALTH_TEST_CLIENT_SECRET")
    if not (refresh_token and client_id and client_secret):
        pytest.skip("set GOOGLE_HEALTH_TEST_* env vars to enable")

    from django.conf import settings
    from django.contrib.auth import get_user_model

    settings.GOOGLE_HEALTH_CLIENT_ID = client_id
    settings.GOOGLE_HEALTH_CLIENT_SECRET = client_secret

    User = get_user_model()
    customer = User.objects.create_user(username="live-sync-test")
    conn = GoogleHealthConnection.objects.create(
        customer=customer,
        google_user_id="placeholder",
        access_token="placeholder",
        refresh_token=refresh_token,
        token_expires_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        scopes=[SCOPE_ACTIVITY_AND_FITNESS_READONLY],
    )
    # Resolve google_user_id before sync (would otherwise be set by an initial
    # ingest_tokens call; not exercised here).
    oauth.refresh_access_token(conn)
    with GoogleHealthClient(conn) as client:
        identity = client.get_identity()
    conn.google_user_id = identity.get("googleUserId") or identity.get("healthUserId")
    conn.save(update_fields=["google_user_id"])

    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=24)
    result = ingest.sync_user(conn, start=start, end=end, data_types=[DATA_TYPE_STEPS])
    assert DATA_TYPE_STEPS in result.counts
