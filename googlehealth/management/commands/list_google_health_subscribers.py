"""List Google Health webhook subscribers registered to a project."""

from __future__ import annotations

import json

from django.core.management.base import BaseCommand, CommandError

from ...webhooks import WebhookError, list_subscribers


class Command(BaseCommand):
    help = "List all Google Health webhook subscribers for a Google Cloud project."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--project-id", required=True)

    def handle(self, *args, **options) -> None:
        try:
            response = list_subscribers(project_id=options["project_id"])
        except WebhookError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(json.dumps(response, indent=2))
