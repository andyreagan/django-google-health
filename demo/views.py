"""Tiny user-facing views so you can click through the OAuth + sync flow
without bouncing through Django's admin.

* ``home`` — show connection status, link to start OAuth, button to trigger sync.
* ``sync`` — POST handler that runs ``sync_user`` for the requesting user and
  redirects home with a flash message.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from googlehealth.ingest import sync_user
from googlehealth.models import GoogleHealthConnection


@login_required
def home(request: HttpRequest) -> HttpResponse:
    connection = GoogleHealthConnection.objects.filter(customer=request.user).first()

    from healthdatamodel.models import Record, Workout

    record_count = Record.objects.filter(customer=request.user).count()
    workout_count = Workout.objects.filter(customer=request.user).count()

    return render(
        request,
        "demo/home.html",
        {
            "connection": connection,
            "record_count": record_count,
            "workout_count": workout_count,
        },
    )


@login_required
@require_POST
def sync(request: HttpRequest) -> HttpResponse:
    try:
        connection = GoogleHealthConnection.objects.get(customer=request.user)
    except GoogleHealthConnection.DoesNotExist:
        messages.error(request, "Connect Google Health first.")
        return redirect("demo-home")

    days = int(request.POST.get("days", "7"))
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)

    try:
        result = sync_user(connection, start=start, end=end)
    except Exception as exc:  # noqa: BLE001 — surface anything to the demo user
        messages.error(request, f"Sync failed: {exc}")
        return redirect("demo-home")

    summary = ", ".join(f"{k}={v}" for k, v in result.counts.items())
    messages.success(request, f"Synced {result.total} record(s): {summary}")
    return redirect("demo-home")
