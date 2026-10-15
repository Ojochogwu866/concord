from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser

from suggestions.generation import SuggestionsDisabledError, suggest_fixes


class Command(BaseCommand):
    help = (
        "Draft fixes for open findings with the configured provider, for editors to "
        "review. Each run asks for at most --limit suggestions. Safe to re-run."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--limit",
            type=int,
            default=settings.SUGGESTIONS_MAX_PER_RUN,
            help="Maximum number of findings to draft fixes for in this run.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        limit = options["limit"]
        if limit < 1:
            raise CommandError("--limit must be at least 1.")
        try:
            report = suggest_fixes(limit)
        except SuggestionsDisabledError as error:
            raise CommandError(str(error)) from error
        self.stdout.write(
            self.style.SUCCESS(
                f"Drafted {report.created} suggestions; {report.failed} failed."
            )
        )
