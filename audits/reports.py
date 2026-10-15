import uuid
from dataclasses import dataclass
from datetime import datetime

from django.db.models import Case, IntegerField, QuerySet, Value, When
from django.utils.translation import get_language
from wagtail.models import Page

from audits.models import AuditRun, Finding

LOG_ENTRY_LIMIT = 8
COMPLETED_STATUSES = [AuditRun.Status.SUCCEEDED, AuditRun.Status.PARTIAL]


@dataclass(frozen=True)
class LogEntry:
    severity: str
    severity_label: str
    code: str
    page_title: str
    page_url: str
    language_code: str
    first_seen_at: datetime


@dataclass(frozen=True)
class InspectionLog:
    latest_run: AuditRun | None
    failed_run: AuditRun | None
    entries: list[LogEntry]
    open_count: int

    @property
    def has_run(self) -> bool:
        return self.latest_run is not None

    @property
    def hidden_count(self) -> int:
        return self.open_count - len(self.entries)


def inspection_log() -> InspectionLog:
    latest_run = AuditRun.objects.filter(status__in=COMPLETED_STATUSES).first()
    newest_attempt = AuditRun.objects.exclude(status=AuditRun.Status.RUNNING).first()
    failed_run = (
        newest_attempt
        if newest_attempt and newest_attempt.status == AuditRun.Status.FAILED
        else None
    )
    open_findings = Finding.objects.filter(resolved_at__isnull=True)
    return InspectionLog(
        latest_run=latest_run,
        failed_run=failed_run,
        entries=_log_entries(open_findings) if latest_run else [],
        open_count=open_findings.count() if latest_run else 0,
    )


def _log_entries(open_findings: QuerySet[Finding]) -> list[LogEntry]:
    findings = list(
        open_findings.select_related("page", "locale")
        .annotate(severity_rank=_severity_rank())
        .order_by("severity_rank", "-first_seen_at")[:LOG_ENTRY_LIMIT]
    )
    localized = _pages_in_current_language([f.page for f in findings if f.page])
    entries = []
    for finding in findings:
        page = finding.page
        shown = localized.get(page.translation_key, page) if page else None
        entries.append(
            LogEntry(
                severity=finding.severity,
                severity_label=finding.get_severity_display(),
                code=finding.code,
                page_title=shown.title if shown else "",
                page_url=shown.url if shown else "",
                language_code=finding.locale.language_code if finding.locale else "",
                first_seen_at=finding.first_seen_at,
            )
        )
    return entries


def _severity_rank() -> Case:
    return Case(
        When(severity=Finding.Severity.ERROR, then=Value(0)),
        default=Value(1),
        output_field=IntegerField(),
    )


def _pages_in_current_language(pages: list[Page]) -> dict[uuid.UUID, Page]:
    keys = {page.translation_key for page in pages}
    translations = Page.objects.live().filter(
        translation_key__in=keys, locale__language_code=get_language()
    )
    return {page.translation_key: page for page in translations}
