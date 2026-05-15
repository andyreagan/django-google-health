"""Tests for the sync_google_health management command."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from googlehealth.constants import DATA_TYPE_STEPS, SCOPE_ACTIVITY_AND_FITNESS_READONLY
from googlehealth.ingest import SyncResult
from googlehealth.models import ConnectionStatus, GoogleHealthConnection

pytestmark = pytest.mark.django_db


@pytest.fixture
def two_active_connections(customer, django_user_model):
    other = django_user_model.objects.create_user(username="other-user")
    a = GoogleHealthConnection.objects.create(
        customer=customer,
        google_user_id="g-a",
        access_token="a",
        refresh_token="r",
        token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        scopes=[SCOPE_ACTIVITY_AND_FITNESS_READONLY],
    )
    b = GoogleHealthConnection.objects.create(
        customer=other,
        google_user_id="g-b",
        access_token="a",
        refresh_token="r",
        token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        scopes=[SCOPE_ACTIVITY_AND_FITNESS_READONLY],
    )
    return a, b


def _fake_result(total: int = 3) -> SyncResult:
    return SyncResult(counts={DATA_TYPE_STEPS: total})


def test_default_window_is_last_24h(two_active_connections):
    out = StringIO()
    with patch("googlehealth.management.commands.sync_google_health.sync_user") as m:
        m.return_value = _fake_result()
        call_command("sync_google_health", stdout=out)
    assert m.call_count == 2
    for call in m.call_args_list:
        start = call.kwargs["start"]
        end = call.kwargs["end"]
        assert end - start == timedelta(hours=24)


def test_filters_by_username(customer, two_active_connections):
    out = StringIO()
    with patch("googlehealth.management.commands.sync_google_health.sync_user") as m:
        m.return_value = _fake_result()
        call_command("sync_google_health", "--user", customer.username, stdout=out)
    assert m.call_count == 1
    assert m.call_args.args[0].customer_id == customer.pk


def test_filters_by_user_id(customer, two_active_connections):
    out = StringIO()
    with patch("googlehealth.management.commands.sync_google_health.sync_user") as m:
        m.return_value = _fake_result()
        call_command("sync_google_health", "--user-id", str(customer.pk), stdout=out)
    assert m.call_count == 1


def test_explicit_start_end(two_active_connections):
    out = StringIO()
    with patch("googlehealth.management.commands.sync_google_health.sync_user") as m:
        m.return_value = _fake_result()
        call_command(
            "sync_google_health",
            "--start",
            "2026-05-01T00:00:00+00:00",
            "--end",
            "2026-05-08T00:00:00+00:00",
            stdout=out,
        )
    call = m.call_args
    assert call.kwargs["end"] - call.kwargs["start"] == timedelta(days=7)


def test_days_window(two_active_connections):
    out = StringIO()
    with patch("googlehealth.management.commands.sync_google_health.sync_user") as m:
        m.return_value = _fake_result()
        call_command("sync_google_health", "--days", "3", stdout=out)
    assert m.call_args.kwargs["end"] - m.call_args.kwargs["start"] == timedelta(days=3)


def test_data_type_filter_passed_through(two_active_connections):
    out = StringIO()
    with patch("googlehealth.management.commands.sync_google_health.sync_user") as m:
        m.return_value = _fake_result()
        call_command(
            "sync_google_health",
            "--data-type",
            "steps",
            "--data-type",
            "sleep",
            stdout=out,
        )
    assert m.call_args.kwargs["data_types"] == ["steps", "sleep"]


def test_skips_disconnected_and_revoked(customer):
    GoogleHealthConnection.objects.create(
        customer=customer,
        google_user_id="g",
        access_token="a",
        refresh_token="r",
        token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        scopes=[],
        status=ConnectionStatus.REVOKED,
    )
    out = StringIO()
    with patch("googlehealth.management.commands.sync_google_health.sync_user") as m:
        call_command("sync_google_health", stdout=out)
    m.assert_not_called()
    assert "No matching active connections" in out.getvalue()


def test_continues_after_failure_and_raises_at_end(two_active_connections):
    out, err = StringIO(), StringIO()
    with patch("googlehealth.management.commands.sync_google_health.sync_user") as m:
        m.side_effect = [_fake_result(), RuntimeError("boom")]
        with pytest.raises(CommandError):
            call_command("sync_google_health", stdout=out, stderr=err)
    assert m.call_count == 2
    assert "failed" in err.getvalue()


def test_invalid_start_end_pairing():
    with pytest.raises(CommandError, match="must be used together"):
        call_command("sync_google_health", "--start", "2026-05-01T00:00:00Z")


def test_unknown_user_raises():
    with pytest.raises(CommandError, match="No user with"):
        call_command("sync_google_health", "--user", "ghost")
