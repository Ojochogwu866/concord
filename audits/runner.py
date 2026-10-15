import logging
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime

from bs4 import BeautifulSoup
from django.db import transaction
from django.utils import timezone
from wagtail.models import Locale, Page

from audits.models import AuditRun, Finding
from audits.registry import (
    FindingData,
    InspectedPage,
    registered_checks,
    registered_site_checks,
)
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
class PageFailure:
    page_id: int
    path: str
    reason: str


def run_page_audit() -> AuditRun:
    run = AuditRun.objects.create(kind=AuditRun.Kind.PAGES)
    try:
        return _complete_run(run)
    except Exception:
        logger.exception("Audit run %s stopped unexpectedly.", run.pk)
        run.status = AuditRun.Status.FAILED
        run.finished_at = timezone.now()
        run.save(update_fields=["status", "finished_at"])
        raise


def _complete_run(run: AuditRun) -> AuditRun:
    pages = list(
        Page.objects.live()
        .filter(depth__gt=1)
        .select_related("locale")
        .order_by("path")
    )
    locale_ids = dict(Locale.objects.values_list("language_code", "pk"))
    detected, failures = _inspect_pages(run, pages, locale_ids)
    detected.extend(_run_site_checks(locale_ids))

    with transaction.atomic():
        open_by_code = _sync_findings(run, detected, {f.page_id for f in failures})
        run.pages_inspected = len(pages) - len(failures)
        run.pages_failed = len(failures)
        run.status = _status_for(len(pages), len(failures))
        run.summary = {
            "open_by_code": dict(open_by_code),
            "failed_pages": [failure.__dict__ for failure in failures],
        }
        run.finished_at = timezone.now()
        run.save()
    return run


def _inspect_pages(
    run: AuditRun, pages: list[Page], locale_ids: dict[str, int]
) -> tuple[list[DetectedFinding], list[PageFailure]]:
    translations = _live_pages_by_translation_key(pages)
    detected: list[DetectedFinding] = []
    failures: list[PageFailure] = []
    for page in pages:
        path = page.get_url()
        try:
            html = render_page_html(path)
        except PageRenderError as error:
            logger.warning("Audit run %s skipped page %s: %s", run.pk, page.pk, error)
            failures.append(PageFailure(page_id=page.pk, path=path, reason=str(error)))
            continue
        inspected = InspectedPage(
            page=page,
            url=path,
            html=BeautifulSoup(html, "html.parser"),
            translations=translations[page.translation_key],
        )
        detected.extend(_inspect(inspected, locale_ids))
    return detected, failures


def _inspect(
    inspected: InspectedPage, locale_ids: dict[str, int]
) -> list[DetectedFinding]:
    page_url = inspected.page.get_full_url() or inspected.url
    return [
        DetectedFinding(
            page=inspected.page,
            page_url=page_url,
            locale_id=(
                locale_ids[data.language_code]
                if data.language_code
                else inspected.page.locale_id
            ),
            data=data,
        )
        for check in registered_checks()
        for data in check(inspected)
    ]


def _run_site_checks(locale_ids: dict[str, int]) -> list[DetectedFinding]:
    return [
        DetectedFinding(
            page=None,
            page_url=data.url,
            locale_id=locale_ids.get(data.language_code)
            if data.language_code
            else None,
            data=data,
        )
        for check in registered_site_checks()
        for data in check()
    ]


def _sync_findings(
    run: AuditRun, detected: list[DetectedFinding], skipped_page_ids: set[int]
) -> Counter[str]:
    now = timezone.now()
    open_findings = {
        (finding.code, finding.page_id, finding.locale_id, finding.fingerprint): finding
        for finding in Finding.objects.filter(resolved_at__isnull=True)
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


def _live_pages_by_translation_key(
    pages: list[Page],
) -> defaultdict[uuid.UUID, dict[str, Page]]:
    index: defaultdict[uuid.UUID, dict[str, Page]] = defaultdict(dict)
    for page in pages:
        index[page.translation_key][page.locale.language_code] = page
    return index


def _status_for(page_count: int, failure_count: int) -> AuditRun.Status:
    if failure_count == 0:
        return AuditRun.Status.SUCCEEDED
    if failure_count < page_count:
        return AuditRun.Status.PARTIAL
    return AuditRun.Status.FAILED
