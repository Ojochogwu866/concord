from typing import Any

from django.core.management.base import BaseCommand, CommandError

from audits.links import run_link_check
from audits.models import AuditRun


class Command(BaseCommand):
    help = (
        "Check every link on every live page. A link is reported as broken only "
        "after three failed checks in a row. Safe to re-run."
    )

    def handle(self, *args: Any, **options: Any) -> None:
        run = run_link_check()
        summary = run.summary
        report = (
            f"Run {run.pk}: checked {summary.get('links_checked', 0)} links on "
            f"{run.pages_inspected} pages, {summary.get('failing_now', 0)} failing now."
        )
        if run.status == AuditRun.Status.FAILED:
            raise CommandError(f"{report} No page could be rendered.")
        if run.status == AuditRun.Status.PARTIAL:
            self.stdout.write(
                self.style.WARNING(f"{report} {run.pages_failed} pages failed.")
            )
            return
        self.stdout.write(self.style.SUCCESS(report))
