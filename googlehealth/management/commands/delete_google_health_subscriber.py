"""Delete a Google Health webhook subscriber."""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from ...webhooks import WebhookError, delete_subscriber


class Command(BaseCommand):
    help = "Delete a Google Health webhook subscriber."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--project-id", required=True)
        parser.add_argument("--subscriber-id", required=True)

    def handle(self, *args, **options) -> None:
        try:
            delete_subscriber(
                project_id=options["project_id"],
                subscriber_id=options["subscriber_id"],
            )
        except WebhookError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(
            self.style.SUCCESS(f"Deleted subscriber {options['subscriber_id']!r}.")
        )
