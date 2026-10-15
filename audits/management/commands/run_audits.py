from typing import Any

from django.core.management.base import BaseCommand, CommandError

from audits.models import AuditRun, Finding
from audits.runner import run_page_audit


class Command(BaseCommand):
    help = "Inspect every live page and record what the checks find. Safe to re-run."

    def handle(self, *args: Any, **options: Any) -> None:
        run = run_page_audit()
        open_count = Finding.objects.filter(resolved_at__isnull=True).count()
        report = (
            f"Run {run.pk}: inspected {run.pages_inspected} pages, "
            f"{open_count} open findings."
        )
        if run.status == AuditRun.Status.FAILED:
            raise CommandError(f"{report} No page could be rendered.")
        if run.status == AuditRun.Status.PARTIAL:
            self.stdout.write(
                self.style.WARNING(f"{report} {run.pages_failed} pages failed.")
            )
            return
        self.stdout.write(self.style.SUCCESS(report))
