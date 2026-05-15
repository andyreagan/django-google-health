"""Create a Google Health webhook subscriber.

Requires Application Default Credentials. The simplest way to set them up
locally is ``gcloud auth application-default login``; production should use a
service account JSON via ``GOOGLE_APPLICATION_CREDENTIALS``.

Example::

    python manage.py create_google_health_subscriber \\
        --project-id my-gcp-project \\
        --subscriber-id my-app-prod \\
        --endpoint-uri https://api.example.com/google-health/notifications/ \\
        --data-types steps,sleep,weight \\
        --policy AUTOMATIC \\
        --secret "Bearer $(openssl rand -hex 32)"
"""

from __future__ import annotations

import json

from django.core.management.base import BaseCommand, CommandError

from ...webhooks import WebhookError, create_subscriber


class Command(BaseCommand):
    help = (
        "Register a Google Health webhook subscriber via projects.subscribers.create."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument("--project-id", required=True)
        parser.add_argument("--subscriber-id", required=True)
        parser.add_argument("--endpoint-uri", required=True)
        parser.add_argument(
            "--data-types",
            required=True,
            help="Comma-separated data type identifiers (e.g. steps,sleep,weight).",
        )
        parser.add_argument(
            "--policy",
            choices=("AUTOMATIC", "MANUAL"),
            default="AUTOMATIC",
            help="subscriptionCreatePolicy applied to every data type.",
        )
        parser.add_argument(
            "--secret",
            required=True,
            help='Full Authorization-header value Google echoes back (e.g. "Bearer ...").',
        )

    def handle(self, *args, **options) -> None:
        data_types = [t.strip() for t in options["data_types"].split(",") if t.strip()]
        configs = [
            {"dataTypes": data_types, "subscriptionCreatePolicy": options["policy"]}
        ]
        try:
            response = create_subscriber(
                project_id=options["project_id"],
                subscriber_id=options["subscriber_id"],
                endpoint_uri=options["endpoint_uri"],
                subscriber_configs=configs,
                authorization_secret=options["secret"],
            )
        except WebhookError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(json.dumps(response, indent=2))
