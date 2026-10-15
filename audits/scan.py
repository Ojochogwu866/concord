import logging
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime

from django.db.models import QuerySet
from django.utils import timezone
from wagtail.models import Page

from audits.models import AuditRun, Finding
from audits.registry import FindingData
from audits.rendering import PageRenderError, render_page_html

logger = logging.getLogger(__name__)

FindingKey = tuple[str, int | None, int | None, str]


@dataclass(frozen=True)
class DetectedFinding:
    page: Page | None
    page_url: str
    locale_id: int | None
    data: FindingData

    @property
    def key(self) -> FindingKey:
        page_id = self.page.pk if self.page else None
        return (self.data.code, page_id, self.locale_id, self.data.fingerprint)


@dataclass(frozen=True)
class RenderedPage:
    page: Page
    path: str
    html: str


@dataclass(frozen=True)
class PageFailure:
    page_id: int
    path: str
    reason: str


def live_pages() -> list[Page]:
    pages: QuerySet[Page] = (
        Page.objects.live()
        .filter(depth__gt=1)
        .select_related("locale")
        .order_by("path")
    )
    return list(pages)


def render_pages(
    run: AuditRun, pages: list[Page]
) -> tuple[list[RenderedPage], list[PageFailure]]:
    rendered: list[RenderedPage] = []
    failures: list[PageFailure] = []
    for page in pages:
        path = page.get_url()
        try:
            rendered.append(
                RenderedPage(page=page, path=path, html=render_page_html(path))
            )
        except PageRenderError as error:
            logger.warning("Run %s skipped page %s: %s", run.pk, page.pk, error)
            failures.append(PageFailure(page_id=page.pk, path=path, reason=str(error)))
    return rendered, failures


@contextmanager
def failure_recorded(run: AuditRun) -> Iterator[None]:
    try:
        yield
    except Exception:
        logger.exception("Run %s stopped unexpectedly.", run.pk)
        run.status = AuditRun.Status.FAILED
        run.finished_at = timezone.now()
        run.save(update_fields=["status", "finished_at"])
        raise


def sync_findings(
    run: AuditRun, detected: list[DetectedFinding], skipped_page_ids: set[int]
) -> Counter[str]:
    now = timezone.now()
    # Each kind of run only resolves findings it raised, so a page audit can never
    # close a broken link and a link check can never close a translation gap.
    open_findings = {
        (finding.code, finding.page_id, finding.locale_id, finding.fingerprint): finding
        for finding in Finding.objects.filter(
            resolved_at__isnull=True, run__kind=run.kind
        )
    }

    seen: dict[FindingKey, DetectedFinding] = {}
    for item in detected:
        seen.setdefault(item.key, item)

    new_findings, still_open = [], []
    for key, item in seen.items():
        existing = open_findings.get(key)
        if existing is None:
            new_findings.append(_new_finding(run, item, now))
        else:
            existing.severity = item.data.severity
            existing.message = item.data.message
            existing.url = item.page_url
            existing.last_seen_at = now
            still_open.append(existing)

    Finding.objects.bulk_create(new_findings)
    Finding.objects.bulk_update(
        still_open, ["severity", "message", "url", "last_seen_at"]
    )
    resolved_ids = [
        finding.pk
        for key, finding in open_findings.items()
        if key not in seen and finding.page_id not in skipped_page_ids
    ]
    Finding.objects.filter(pk__in=resolved_ids).update(resolved_at=now)
    return Counter(item.data.code for item in seen.values())


def finish_run(
    run: AuditRun,
    page_count: int,
    failures: list[PageFailure],
    summary: dict[str, object],
) -> None:
    run.pages_inspected = page_count - len(failures)
    run.pages_failed = len(failures)
    run.status = _status_for(page_count, len(failures))
    run.summary = {
        **summary,
        "failed_pages": [failure.__dict__ for failure in failures],
    }
    run.finished_at = timezone.now()
    run.save()


def _new_finding(run: AuditRun, item: DetectedFinding, now: datetime) -> Finding:
    return Finding(
        run=run,
        page=item.page,
        locale_id=item.locale_id,
        code=item.data.code,
        severity=item.data.severity,
        message=item.data.message,
        url=item.page_url,
        fingerprint=item.data.fingerprint,
        first_seen_at=now,
        last_seen_at=now,
    )


def _status_for(page_count: int, failure_count: int) -> AuditRun.Status:
    if failure_count == 0:
        return AuditRun.Status.SUCCEEDED
    if failure_count < page_count:
        return AuditRun.Status.PARTIAL
    return AuditRun.Status.FAILED
