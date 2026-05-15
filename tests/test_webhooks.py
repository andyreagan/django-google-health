"""Tests for googlehealth.webhooks + the notification_receiver view."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from io import StringIO
from unittest.mock import patch

import pytest
import respx
from django.core.management import call_command
from django.core.management.base import CommandError
from django.dispatch import receiver
from httpx import Response

from googlehealth import webhooks
from googlehealth.constants import API_BASE_URL, API_VERSION
from googlehealth.signals import notification_received

PROJECT_ID = "demo-project"
SUBSCRIBER_ID = "demo-subscriber"
SECRET = "Bearer demo-secret-abc123"

PROJECTS_BASE = f"{API_BASE_URL}/{API_VERSION}/projects/{PROJECT_ID}/subscribers"


def _patch_admin_token():
    """Stub Application Default Credentials so unit tests don't need ADC."""
    return patch.object(webhooks, "_admin_bearer_token", return_value="admin-token")


# ---------------------------------------------------------------------------
# Subscriber CRUD
# ---------------------------------------------------------------------------


@respx.mock
def test_create_subscriber_posts_expected_payload():
    expected_resp = {"name": f"projects/{PROJECT_ID}/subscribers/{SUBSCRIBER_ID}"}
    route = respx.post(PROJECTS_BASE).mock(
        return_value=Response(200, json=expected_resp)
    )

    with _patch_admin_token():
        result = webhooks.create_subscriber(
            project_id=PROJECT_ID,
            subscriber_id=SUBSCRIBER_ID,
            endpoint_uri="https://api.example.com/google-health/notifications/",
            subscriber_configs=[
                {
                    "dataTypes": ["steps", "sleep"],
                    "subscriptionCreatePolicy": "AUTOMATIC",
                }
            ],
            authorization_secret=SECRET,
        )

    assert result == expected_resp
    req = route.calls.last.request
    body = json.loads(req.content)
    assert body["endpointUri"] == "https://api.example.com/google-health/notifications/"
    assert body["endpointAuthorization"]["secret"] == SECRET
    assert req.url.params["subscriberId"] == SUBSCRIBER_ID
    assert req.headers["Authorization"] == "Bearer admin-token"


@respx.mock
def test_create_subscriber_raises_on_error():
    respx.post(PROJECTS_BASE).mock(
        return_value=Response(403, json={"error": {"message": "permission denied"}})
    )
    with _patch_admin_token(), pytest.raises(webhooks.WebhookError) as exc:
        webhooks.create_subscriber(
            project_id=PROJECT_ID,
            subscriber_id=SUBSCRIBER_ID,
            endpoint_uri="https://example.com",
            subscriber_configs=[],
            authorization_secret=SECRET,
        )
    assert exc.value.status_code == 403


@respx.mock
def test_list_and_delete_subscriber():
    respx.get(PROJECTS_BASE).mock(return_value=Response(200, json={"subscribers": []}))
    respx.delete(f"{PROJECTS_BASE}/{SUBSCRIBER_ID}").mock(
        return_value=Response(200, json={})
    )

    with _patch_admin_token():
        assert webhooks.list_subscribers(project_id=PROJECT_ID) == {"subscribers": []}
        assert (
            webhooks.delete_subscriber(
                project_id=PROJECT_ID, subscriber_id=SUBSCRIBER_ID
            )
            == {}
        )


# ---------------------------------------------------------------------------
# Receiver view: verification handshake + auth + signal emission
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def webhook_secret(settings):
    settings.GOOGLE_HEALTH_WEBHOOK_AUTHORIZATION = SECRET


def test_verification_handshake_with_auth_returns_200(client):
    response = client.post(
        "/google-health/notifications/",
        data=json.dumps({"type": "verification"}),
        content_type="application/json",
        HTTP_AUTHORIZATION=SECRET,
    )
    assert response.status_code == 200


def test_verification_handshake_without_auth_returns_401(client):
    response = client.post(
        "/google-health/notifications/",
        data=json.dumps({"type": "verification"}),
        content_type="application/json",
    )
    assert response.status_code == 401


def test_notification_with_bad_auth_returns_401(client):
    response = client.post(
        "/google-health/notifications/",
        data=json.dumps({"data": {"healthUserId": "x"}}),
        content_type="application/json",
        HTTP_AUTHORIZATION="Bearer wrong",
    )
    assert response.status_code == 401


def test_notification_with_good_auth_returns_204_and_emits_signal(client):
    received: list[dict] = []

    @receiver(notification_received, weak=False)
    def capture(sender, payload, **kwargs):
        received.append(payload)

    try:
        response = client.post(
            "/google-health/notifications/",
            data=json.dumps({"data": {"healthUserId": "u1", "dataType": "steps"}}),
            content_type="application/json",
            HTTP_AUTHORIZATION=SECRET,
        )
    finally:
        notification_received.disconnect(capture)

    assert response.status_code == 204
    assert received == [{"data": {"healthUserId": "u1", "dataType": "steps"}}]


def test_notification_with_invalid_json_returns_400(client):
    response = client.post(
        "/google-health/notifications/",
        data=b"\x80not-json",
        content_type="application/json",
        HTTP_AUTHORIZATION=SECRET,
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# process_notification — wires payload → connection → sync_user
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_process_notification_drives_sync_user_with_interval_window(connection):
    connection.google_user_id = "user-123"
    connection.save()

    payload = {
        "data": {
            "healthUserId": "user-123",
            "dataType": "steps",
            "intervals": [
                {
                    "physicalTimeInterval": {
                        "startTime": "2026-05-01T01:00:00Z",
                        "endTime": "2026-05-01T01:15:00Z",
                    }
                },
                {
                    "physicalTimeInterval": {
                        "startTime": "2026-05-01T02:30:00Z",
                        "endTime": "2026-05-01T02:45:00Z",
                    }
                },
            ],
        }
    }

    with patch("googlehealth.webhooks.sync_user") as m:
        webhooks.process_notification(payload)

    m.assert_called_once()
    kwargs = m.call_args.kwargs
    assert kwargs["start"] == datetime(2026, 5, 1, 1, 0, tzinfo=timezone.utc)
    assert kwargs["end"] == datetime(2026, 5, 1, 2, 45, tzinfo=timezone.utc)
    assert kwargs["data_types"] == ["steps"]


@pytest.mark.django_db
def test_process_notification_skips_unknown_user(connection, caplog):
    payload = {
        "data": {
            "healthUserId": "no-such-user",
            "dataType": "steps",
            "intervals": [
                {
                    "physicalTimeInterval": {
                        "startTime": "2026-05-01T00:00:00Z",
                        "endTime": "2026-05-01T01:00:00Z",
                    }
                }
            ],
        }
    }
    with patch("googlehealth.webhooks.sync_user") as m:
        webhooks.process_notification(payload)
    m.assert_not_called()


@pytest.mark.django_db
def test_process_notification_skips_payload_with_missing_fields(connection):
    with patch("googlehealth.webhooks.sync_user") as m:
        webhooks.process_notification({"data": {}})
    m.assert_not_called()


# ---------------------------------------------------------------------------
# Management commands
# ---------------------------------------------------------------------------


@respx.mock
def test_create_command_invokes_create_subscriber():
    respx.post(PROJECTS_BASE).mock(return_value=Response(200, json={"ok": True}))
    out = StringIO()
    with _patch_admin_token():
        call_command(
            "create_google_health_subscriber",
            "--project-id",
            PROJECT_ID,
            "--subscriber-id",
            SUBSCRIBER_ID,
            "--endpoint-uri",
            "https://example.com/cb",
            "--data-types",
            "steps,sleep",
            "--secret",
            SECRET,
            stdout=out,
        )
    assert json.loads(out.getvalue()) == {"ok": True}


@respx.mock
def test_list_command_dumps_response():
    respx.get(PROJECTS_BASE).mock(
        return_value=Response(200, json={"subscribers": [{"name": "x"}]})
    )
    out = StringIO()
    with _patch_admin_token():
        call_command(
            "list_google_health_subscribers", "--project-id", PROJECT_ID, stdout=out
        )
    assert json.loads(out.getvalue()) == {"subscribers": [{"name": "x"}]}


@respx.mock
def test_delete_command_succeeds():
    respx.delete(f"{PROJECTS_BASE}/{SUBSCRIBER_ID}").mock(
        return_value=Response(200, json={})
    )
    out = StringIO()
    with _patch_admin_token():
        call_command(
            "delete_google_health_subscriber",
            "--project-id",
            PROJECT_ID,
            "--subscriber-id",
            SUBSCRIBER_ID,
            stdout=out,
        )
    assert "Deleted subscriber" in out.getvalue()


@respx.mock
def test_create_command_translates_webhook_error_to_command_error():
    respx.post(PROJECTS_BASE).mock(
        return_value=Response(400, json={"error": {"message": "bad config"}})
    )
    with _patch_admin_token(), pytest.raises(CommandError, match="bad config"):
        call_command(
            "create_google_health_subscriber",
            "--project-id",
            PROJECT_ID,
            "--subscriber-id",
            SUBSCRIBER_ID,
            "--endpoint-uri",
            "https://example.com/cb",
            "--data-types",
            "steps",
            "--secret",
            SECRET,
        )
