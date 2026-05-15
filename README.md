# django-google-health

[![CI](https://github.com/andyreagan/django-google-health/actions/workflows/ci.yml/badge.svg)](https://github.com/andyreagan/django-google-health/actions/workflows/ci.yml)

A reusable Django app for the [Google Health API](https://developers.google.com/health) — the successor to the Fitbit Web API. Handles the Google OAuth 2.0 flow, fetches user health data from `health.googleapis.com`, and persists it through [`django-healthdatamodel`](https://github.com/andyreagan/django-healthdatamodel) so the same storage and query layer serves Apple Health, Fitbit, and Google Health side-by-side.

> Google recommends launching new integrations **after the end of May 2026** to align with legacy Fitbit account deprecation. See `docs/google-health/get-started.md`.

## Status

Early scaffolding. The package, demo project, OAuth model, and CI are in place. OAuth views, the HTTP client, ingest mapping, and webhook handling are stubbed and will land in follow-up slices.

## Install

```
pip install django-google-health
```

Add both this app and `django-healthdatamodel` to `INSTALLED_APPS`, then run migrations:

```python
INSTALLED_APPS = [
    ...
    "healthdatamodel",
    "googlehealth",
]
```

```
python manage.py migrate
```

The model uses `settings.AUTH_USER_MODEL` so it works with any custom user model.

## Configuration

```python
GOOGLE_HEALTH_CLIENT_ID = "..."        # from Google Cloud Console
GOOGLE_HEALTH_CLIENT_SECRET = "..."
GOOGLE_HEALTH_REDIRECT_URI = "https://your-app.example.com/google-health/callback"
```

Set up the OAuth client in [Google Cloud Console](https://console.cloud.google.com/) and enable the Google Health API. See `docs/google-health/codelabs-make-your-first-api-call.md` for a step-by-step walkthrough.

## Scopes

Google Health scopes are namespaced under `https://www.googleapis.com/auth/googlehealth.*`. The complete list lives in `googlehealth.constants` and is documented in `docs/google-health/scopes.md`. Examples:

- `googlehealth.activity_and_fitness.readonly` — steps, distance, exercise, floors, altitude
- `googlehealth.health_metrics_and_measurements.readonly` — heart rate, weight, body fat, SpO2
- `googlehealth.sleep.readonly` — sleep stages and sessions
- `googlehealth.location.readonly` — exercise GPS

## Storage

This app does **not** define `Record` / `Workout` tables — those live in `django-healthdatamodel`. The `googlehealth.ingest` module maps Google Health API responses to `healthdatamodel.schemas.RecordInput` and `WorkoutInput`, then calls `healthdatamodel.ingest.ingest_records` to persist them. Read the data back with `healthdatamodel.query.*` (see that project's docs).

The only model defined here is `GoogleHealthConnection`: per-user OAuth tokens, granted scopes, connection status, and last sync timestamp.

## Documentation

The Google Health API documentation is vendored as Markdown under `docs/google-health/` so it's grep-able offline:

- `get-started.md` — overview, benefits, getting started paths
- `migration.md` — Fitbit Web API → Google Health API migration guide
- `data-types.md` — every data type with operations and scopes
- `scopes.md` — OAuth scopes
- `webhooks.md` — subscriber registration, endpoint verification, notification payloads
- `codelabs-make-your-first-api-call.md` — end-to-end OAuth + first API call
- `reference-rest.md` — REST resource index
- `migration-parity-tool.md` — parity tool reference
- `support.md` — issue tracker and forum links

## Demo project — end-to-end sync against your own Google account

The repo includes a runnable demo Django project at `demo/` that you can use to
go through the full OAuth flow and sync your own Google Health data into
`healthdatamodel`.

### 1. Set up a Google Cloud OAuth client

Follow `docs/google-health/codelabs-make-your-first-api-call.md`. Two things
specific to the demo:

- **Application type:** Web application.
- **Authorized redirect URI:** `http://localhost:8000/google-health/callback/`
  (exact match, trailing slash matters).
- Add yourself as a test user under **Audience**, and add the scopes you want
  from `googlehealth.constants` under **Data Access**. A good starter set is
  `.activity_and_fitness.readonly`, `.health_metrics_and_measurements.readonly`,
  `.sleep.readonly`.

### 2. Run the demo

```
uv sync
uv run python manage.py migrate
uv run python manage.py createsuperuser
export GOOGLE_HEALTH_CLIENT_ID=...
export GOOGLE_HEALTH_CLIENT_SECRET=...
# Google's oauthlib refuses non-HTTPS redirect URIs unless you tell it otherwise.
# This is fine for local dev only:
export OAUTHLIB_INSECURE_TRANSPORT=1
uv run python manage.py runserver
```

### 3. Connect + sync from the browser

Open <http://localhost:8000/>. You'll be redirected to a sign-in page; use the
superuser you just created. The demo homepage gives you:

- A **Connect Google Health** button → kicks off OAuth, returns here.
- Once connected, a **Sync now** form with a "days" input → fetches the
  selected window and persists everything into `healthdatamodel`.
- A running count of records + workouts and a link to the admin to browse them.
- A **Disconnect** button.

If you'd rather drive sync from the terminal (handy for backfills or cron):

```
uv run python manage.py sync_google_health --user <your-username> --days 7
```

## Development

```
uv sync --group dev
uv run pytest tests/ -v
uv run pre-commit run --all-files
```

## Live integration tests

The default test suite mocks all HTTP with [respx](https://lundberg.github.io/respx/) and runs offline. A small subset (marked `@pytest.mark.live`) hits the real `health.googleapis.com` and is skipped unless you set up real credentials.

You need three environment variables, all sourced from your own Google Cloud project:

```
GOOGLE_HEALTH_TEST_CLIENT_ID
GOOGLE_HEALTH_TEST_CLIENT_SECRET
GOOGLE_HEALTH_TEST_REFRESH_TOKEN
```

### 1. Create the OAuth client (one-time)

Follow the codelab in `docs/google-health/codelabs-make-your-first-api-call.md` for the full walkthrough. Condensed:

1. Sign in to [Google Cloud Console](https://console.cloud.google.com/), create a project, and enable the **Google Health API** under **APIs & Services → Library**.
2. **APIs & Services → Credentials → + Create Credentials → OAuth client ID**. Application type: **Web application**. Add `https://www.google.com` to **Authorized redirect URIs** — Google's homepage is the simplest receiver for a one-time manual exchange.
3. Save the client ID and client secret. **The secret is shown only once.**
4. Under **Audience**, add your own Google account (the one signed into the Fitbit app) as a **Test user**.
5. Under **Data Access**, add the scopes you want to test against. For a smoke test of the activity endpoints, `.../auth/googlehealth.activity_and_fitness.readonly` is enough.

### 2. Run the consent flow and capture a refresh token (one-time)

Open this URL in a browser (substituting your client ID), sign in as the test user, and click through the consent screen. `access_type=offline&prompt=consent` guarantees a refresh token even on repeat consents:

```
https://accounts.google.com/o/oauth2/v2/auth?client_id=YOUR_CLIENT_ID&redirect_uri=https://www.google.com&response_type=code&access_type=offline&prompt=consent&scope=https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly
```

After consenting you'll land on `https://www.google.com/?code=<AUTH_CODE>&scope=...`. Copy the value between `code=` and `&scope=`.

Exchange that code for tokens (one shot — auth codes are single-use):

```
curl -s https://oauth2.googleapis.com/token \
  -d code=YOUR_AUTH_CODE \
  -d client_id=YOUR_CLIENT_ID \
  -d client_secret=YOUR_CLIENT_SECRET \
  -d redirect_uri=https://www.google.com \
  -d grant_type=authorization_code
```

Pluck `refresh_token` out of the JSON response and store it somewhere safe. Access tokens expire in 1 hour; the test harness uses the refresh token to mint fresh ones, so you only repeat this step if your refresh token expires (6 months of inactivity) or you revoke consent.

### 3. Run the live tests

```
export GOOGLE_HEALTH_TEST_CLIENT_ID=...
export GOOGLE_HEALTH_TEST_CLIENT_SECRET=...
export GOOGLE_HEALTH_TEST_REFRESH_TOKEN=...
uv run pytest tests/ -v -m live
```

The default `pytest` run skips these. CI does not run live tests — they need credentials that aren't safe to commit.

> The Fitbit mobile app needs to have data in your account for most endpoints to return anything. The codelab walks through manually logging a Walk activity if you don't already have data.
