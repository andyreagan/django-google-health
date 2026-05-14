"""Minimal Django settings for pytest-django."""

SECRET_KEY = "test-secret-key"  # noqa: S105
DEBUG = False

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.admin",
    "django.contrib.messages",
    "django.contrib.sessions",
    "healthdatamodel",
    "googlehealth",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True

GOOGLE_HEALTH_CLIENT_ID = "test-client-id"
GOOGLE_HEALTH_CLIENT_SECRET = "test-client-secret"  # noqa: S105
GOOGLE_HEALTH_REDIRECT_URI = "http://testserver/google-health/callback"
