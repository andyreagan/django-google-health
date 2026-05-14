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

## Demo project

The repo includes a runnable demo Django project under `demo/`:

```
uv sync
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

Visit http://localhost:8000/admin/ to browse the `googlehealth` and `healthdatamodel` apps.

## Development

```
uv sync --group dev
uv run pytest tests/ -v
uv run pre-commit run --all-files
```
