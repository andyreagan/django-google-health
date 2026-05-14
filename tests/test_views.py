from urllib.parse import parse_qs, urlparse

import pytest
import respx
import responses
from httpx import Response

from googlehealth.constants import (
    API_BASE_URL,
    API_VERSION,
    OAUTH_REVOKE_URL,
    OAUTH_TOKEN_URL,
)
from googlehealth.models import ConnectionStatus, GoogleHealthConnection
from googlehealth.views import SESSION_KEY

pytestmark = pytest.mark.django_db


def test_connect_requires_login(client):
    response = client.get("/google-health/connect/")
    assert response.status_code == 302
    assert "/accounts/login/" in response.url or "next=" in response.url


def test_connect_redirects_to_google_and_stashes_state(client, customer):
    client.force_login(customer)
    response = client.get("/google-health/connect/")

    assert response.status_code == 302
    assert response.url.startswith("https://accounts.google.com/")
    stashed = client.session[SESSION_KEY]
    params = {k: v[0] for k, v in parse_qs(urlparse(response.url).query).items()}
    assert stashed["state"] == params["state"]
    assert stashed["code_verifier"] is not None


@respx.mock
@responses.activate
def test_callback_exchanges_code_and_persists_connection(client, customer):
    client.force_login(customer)
    # Prime the session by calling /connect/.
    client.get("/google-health/connect/")
    state = client.session[SESSION_KEY]["state"]

    responses.add(
        responses.POST,
        OAUTH_TOKEN_URL,
        json={
            "access_token": "ya29.cb",
            "expires_in": 3600,
            "refresh_token": "1//cb",
            "token_type": "Bearer",
            "scope": "https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly",
        },
    )
    respx.get(f"{API_BASE_URL}/{API_VERSION}/users/me/identity").mock(
        return_value=Response(200, json={"googleUserId": "callback-user"})
    )

    response = client.get(f"/google-health/callback/?code=abc&state={state}")

    assert response.status_code == 302
    assert response.url == "/admin/"
    conn = GoogleHealthConnection.objects.get(customer=customer)
    assert conn.google_user_id == "callback-user"
    assert conn.access_token == "ya29.cb"


def test_callback_returns_400_on_oauth_error(client, customer):
    client.force_login(customer)
    response = client.get("/google-health/callback/?error=access_denied")
    assert response.status_code == 400


def test_callback_returns_400_on_state_mismatch(client, customer):
    client.force_login(customer)
    client.get("/google-health/connect/")  # stashes a state
    response = client.get("/google-health/callback/?code=abc&state=wrong-state")
    assert response.status_code == 400


def test_callback_returns_400_when_no_flow_in_session(client, customer):
    client.force_login(customer)
    response = client.get("/google-health/callback/?code=abc&state=whatever")
    assert response.status_code == 400


@respx.mock
def test_disconnect_revokes_and_redirects(client, customer, connection):
    client.force_login(customer)
    respx.post(OAUTH_REVOKE_URL).mock(return_value=Response(200))

    response = client.post("/google-health/disconnect/")

    assert response.status_code == 302
    connection.refresh_from_db()
    assert connection.status == ConnectionStatus.REVOKED


def test_disconnect_noop_when_no_connection(client, customer):
    client.force_login(customer)
    response = client.post("/google-health/disconnect/")
    assert response.status_code == 302
