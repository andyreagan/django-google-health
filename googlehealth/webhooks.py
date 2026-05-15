"""Subscriber management and incoming-notification processing.

This module covers four concerns:

* **Subscriber CRUD** (``create_subscriber`` / ``list_subscribers`` /
  ``update_subscriber`` / ``delete_subscriber``) — admin-scoped operations against
  ``/v4/projects/{project-id}/subscribers``. Authenticated with Application
  Default Credentials (a service account or ``gcloud auth application-default
  login``). Requires the ``cloud-platform`` scope.

* **Endpoint verification** — Google performs a two-step handshake when you
  create or update a subscriber. The receiver view in :mod:`googlehealth.views`
  uses :func:`is_verification_payload` and :func:`authorization_matches` to
  satisfy it.

* **Notification authentication** — every incoming notification carries the
  subscriber's configured ``secret`` in its ``Authorization`` header. Match it
  byte-for-byte against ``settings.GOOGLE_HEALTH_WEBHOOK_AUTHORIZATION``.

* **Notification processing** — :func:`process_notification` resolves the
  affected ``GoogleHealthConnection`` by ``healthUserId``, computes the sync
  window from ``intervals[]``, and drives :func:`~googlehealth.ingest.sync_user`.
  Safe to call from a celery worker.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import google.auth
import google.auth.transport.requests
import httpx
from django.conf import settings

from .constants import API_BASE_URL, API_VERSION
from .ingest import sync_user
from .models import GoogleHealthConnection

log = logging.getLogger(__name__)

ADMIN_SCOPES = ("https://www.googleapis.com/auth/cloud-platform",)
VERIFICATION_USER_AGENT = "Google-Health-API-Webhooks-Verifier"


class WebhookError(Exception):
    """Subscriber CRUD failed."""

    def __init__(self, status_code: int, message: str, payload: Any = None):
        super().__init__(f"HTTP {status_code}: {message}")
        self.status_code = status_code
        self.payload = payload


# ---------------------------------------------------------------------------
# Admin auth (Application Default Credentials)
# ---------------------------------------------------------------------------


def _admin_bearer_token() -> str:
    """Mint a fresh access token from ADC. Raises if ADC isn't configured."""
    creds, _ = google.auth.default(scopes=ADMIN_SCOPES)
    creds.refresh(google.auth.transport.requests.Request())
    return creds.token


def _admin_request(
    method: str, path: str, *, params: dict | None = None, json: Any = None
) -> dict[str, Any]:
    url = f"{API_BASE_URL}/{API_VERSION}/{path.lstrip('/')}"
    response = httpx.request(
        method,
        url,
        params=params,
        json=json,
        headers={"Authorization": f"Bearer {_admin_bearer_token()}"},
        timeout=30.0,
    )
    if response.status_code >= 400:
        payload = _safe_json(response)
        raise WebhookError(
            response.status_code,
            _extract_error_message(payload, response.text),
            payload,
        )
    if not response.content:
        return {}
    return response.json()


# ---------------------------------------------------------------------------
# Subscriber CRUD
# ---------------------------------------------------------------------------


def create_subscriber(
    *,
    project_id: str,
    subscriber_id: str,
    endpoint_uri: str,
    subscriber_configs: list[dict[str, Any]],
    authorization_secret: str,
) -> dict[str, Any]:
    """Register a new subscriber. Triggers Google's verification handshake.

    ``authorization_secret`` is the FULL value Google will echo back in the
    ``Authorization`` header on each notification (e.g. ``"Bearer R4nd0m..."``).
    """
    body = {
        "endpointUri": endpoint_uri,
        "subscriberConfigs": subscriber_configs,
        "endpointAuthorization": {"secret": authorization_secret},
    }
    return _admin_request(
        "POST",
        f"projects/{project_id}/subscribers",
        params={"subscriberId": subscriber_id},
        json=body,
    )


def list_subscribers(*, project_id: str) -> dict[str, Any]:
    return _admin_request("GET", f"projects/{project_id}/subscribers")


def update_subscriber(
    *,
    project_id: str,
    subscriber_id: str,
    update_mask: str,
    body: dict[str, Any],
) -> dict[str, Any]:
    return _admin_request(
        "PATCH",
        f"projects/{project_id}/subscribers/{subscriber_id}",
        params={"updateMask": update_mask},
        json=body,
    )


def delete_subscriber(*, project_id: str, subscriber_id: str) -> dict[str, Any]:
    return _admin_request(
        "DELETE", f"projects/{project_id}/subscribers/{subscriber_id}"
    )


# ---------------------------------------------------------------------------
# Incoming-request auth helpers
# ---------------------------------------------------------------------------


def is_verification_payload(payload: Any) -> bool:
    """True if the request body matches Google's verification handshake."""
    return isinstance(payload, dict) and payload.get("type") == "verification"


def authorization_matches(request_auth_header: str | None) -> bool:
    """Compare against ``settings.GOOGLE_HEALTH_WEBHOOK_AUTHORIZATION``.

    Matches the raw header value byte-for-byte — whatever you put in
    ``authorization_secret`` when creating the subscriber.
    """
    expected = getattr(settings, "GOOGLE_HEALTH_WEBHOOK_AUTHORIZATION", None)
    if not expected:
        return False
    return request_auth_header == expected


# ---------------------------------------------------------------------------
# Notification processing
# ---------------------------------------------------------------------------


def process_notification(payload: dict[str, Any]) -> None:
    """Resolve the connection and drive a sync over the notified interval.

    Notifications may be batched (multiple ``intervals``). We compute the union
    of all interval bounds and run a single sync over [min(start), max(end)],
    filtered to the affected ``dataType``.
    """
    data = payload.get("data") or {}
    health_user_id = data.get("healthUserId")
    data_type = data.get("dataType")
    intervals = data.get("intervals") or []
    if not (health_user_id and data_type and intervals):
        log.warning("Skipping notification with missing fields: %r", data)
        return

    try:
        connection = GoogleHealthConnection.objects.get(google_user_id=health_user_id)
    except GoogleHealthConnection.DoesNotExist:
        log.warning("Notification for unknown healthUserId=%s", health_user_id)
        return

    start, end = _span(intervals)
    if start is None or end is None:
        log.warning("Notification had unparseable intervals: %r", intervals)
        return

    sync_user(connection, start=start, end=end, data_types=[data_type])


def _span(intervals: list[dict[str, Any]]) -> tuple[datetime | None, datetime | None]:
    starts: list[datetime] = []
    ends: list[datetime] = []
    for entry in intervals:
        physical = entry.get("physicalTimeInterval") or {}
        start_s = physical.get("startTime")
        end_s = physical.get("endTime")
        if start_s and end_s:
            try:
                starts.append(_parse(start_s))
                ends.append(_parse(end_s))
            except ValueError:
                continue
    if not starts or not ends:
        return None, None
    return min(starts), max(ends)


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _safe_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return None


def _extract_error_message(payload: Any, fallback: str) -> str:
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict) and "message" in error:
            return str(error["message"])
        if isinstance(error, str):
            return error
    return fallback or "(no body)"
