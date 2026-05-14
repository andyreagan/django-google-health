"""OAuth start / callback / disconnect views.

These cover the *web-callback* flow (admin / dev / testing). Mobile clients should
POST tokens (or an auth code) to a project-local endpoint that calls
:func:`googlehealth.oauth.ingest_tokens` or :func:`googlehealth.oauth.exchange_code`.
"""

from __future__ import annotations

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect
from django.views.decorators.http import require_http_methods, require_POST

from . import oauth
from .constants import (
    SCOPE_ACTIVITY_AND_FITNESS_READONLY,
    SCOPE_HEALTH_METRICS_AND_MEASUREMENTS_READONLY,
    SCOPE_SLEEP_READONLY,
)
from .models import GoogleHealthConnection

SESSION_KEY = "googlehealth_oauth_flow"

DEFAULT_SCOPES: tuple[str, ...] = (
    SCOPE_ACTIVITY_AND_FITNESS_READONLY,
    SCOPE_HEALTH_METRICS_AND_MEASUREMENTS_READONLY,
    SCOPE_SLEEP_READONLY,
)


def _scopes() -> list[str]:
    return list(getattr(settings, "GOOGLE_HEALTH_DEFAULT_SCOPES", DEFAULT_SCOPES))


def _success_url() -> str:
    return getattr(settings, "GOOGLE_HEALTH_CONNECT_SUCCESS_URL", "/admin/")


@login_required
@require_http_methods(["GET"])
def connect(request: HttpRequest) -> HttpResponse:
    auth_url, flow_state = oauth.build_authorization_url(scopes=_scopes())
    request.session[SESSION_KEY] = flow_state.model_dump()
    return redirect(auth_url)


@login_required
@require_http_methods(["GET"])
def callback(request: HttpRequest) -> HttpResponse:
    code = request.GET.get("code")
    received_state = request.GET.get("state")
    error = request.GET.get("error")
    if error:
        return HttpResponseBadRequest(f"OAuth error: {error}")
    if not code:
        return HttpResponseBadRequest("Missing authorization code")

    stashed = request.session.pop(SESSION_KEY, None)
    if not stashed:
        return HttpResponseBadRequest("No OAuth flow in progress")
    flow_state = oauth.OAuthFlowState.model_validate(stashed)

    try:
        tokens = oauth.exchange_code(
            code=code,
            scopes=flow_state.scopes,
            code_verifier=flow_state.code_verifier,
            expected_state=flow_state.state,
            received_state=received_state,
        )
    except oauth.StateMismatchError:
        return HttpResponseBadRequest("OAuth state mismatch")

    oauth.ingest_tokens(customer=request.user, tokens=tokens)
    return redirect(_success_url())


@login_required
@require_POST
def disconnect(request: HttpRequest) -> HttpResponse:
    try:
        connection = GoogleHealthConnection.objects.get(customer=request.user)
    except GoogleHealthConnection.DoesNotExist:
        return redirect(_success_url())
    oauth.revoke(connection)
    return redirect(_success_url())
