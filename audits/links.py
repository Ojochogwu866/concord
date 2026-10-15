from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from urllib.parse import urldefrag, urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from wagtail.models import Page

from audits.http import (
    ALLOWED_SCHEMES,
    ExternalLinkChecker,
    HostRateLimiter,
    LinkCheckerLimits,
    LinkResult,
)
from audits.models import AuditRun, Finding, LinkCheck
from audits.registry import FindingData
from audits.rendering import fetch_final_status
from audits.scan import (
    DetectedFinding,
    failure_recorded,
    finish_run,
    live_pages,
    render_pages,
    sync_findings,
)

BROKEN_LINK = "link.broken"
SKIPPED_PREFIXES = ("#", "mailto:", "tel:", "javascript:")
ERROR_MAX_LENGTH = 255
FINGERPRINT_MAX_LENGTH = 255


def run_link_check() -> AuditRun:
    run = AuditRun.objects.create(kind=AuditRun.Kind.LINKS)
    with failure_recorded(run):
        pages = live_pages()
        rendered, failures = render_pages(run, pages)
        links_by_page = {
            item.page: extract_links(item.html, item.page.get_full_url() or "")
            for item in rendered
        }
        site_hosts = {urlsplit(page.get_full_url() or "").netloc for page in pages}
        results = check_urls(set().union(*links_by_page.values()), site_hosts)

        with transaction.atomic():
            checks = _record_results(links_by_page, results)
            detected = _broken_link_findings(checks, {p.pk: p for p in links_by_page})
            open_by_code = sync_findings(run, detected, {f.page_id for f in failures})
            finish_run(
                run,
                len(pages),
                failures,
                {
                    "links_checked": len(results),
                    "failing_now": sum(result.is_broken for result in results.values()),
                    "open_by_code": dict(open_by_code),
                },
            )
    return run


def extract_links(html: str, page_url: str) -> set[str]:
    links = set()
    for anchor in BeautifulSoup(html, "html.parser").find_all("a", href=True):
        href = str(anchor["href"]).strip()
        if not href or href.startswith(SKIPPED_PREFIXES):
            continue
        absolute, _ = urldefrag(urljoin(page_url, href))
        if urlsplit(absolute).scheme in ALLOWED_SCHEMES:
            links.add(absolute)
    return links


def check_urls(urls: set[str], site_hosts: set[str]) -> dict[str, LinkResult]:
    internal = {url for url in urls if urlsplit(url).netloc in site_hosts}
    results = {url: _check_internal(url) for url in internal}
    results.update(_check_external(urls - internal))
    return results


def _check_internal(url: str) -> LinkResult:
    parts = urlsplit(url)
    path = f"{parts.path}?{parts.query}" if parts.query else parts.path
    return LinkResult(url=url, status_code=fetch_final_status(path or "/"))


def _check_external(urls: set[str]) -> dict[str, LinkResult]:
    if not urls:
        return {}
    limits = LinkCheckerLimits(
        max_redirects=settings.LINK_CHECK_MAX_REDIRECTS,
        max_retries=settings.LINK_CHECK_MAX_RETRIES,
        retry_backoff_seconds=settings.LINK_CHECK_RETRY_BACKOFF_SECONDS,
        max_body_bytes=settings.LINK_CHECK_MAX_BODY_BYTES,
    )
    rate_limiter = HostRateLimiter(settings.LINK_CHECK_HOST_INTERVAL_SECONDS)
    user_agent = f"ConcordLinkChecker/1.0 (+{settings.WAGTAILADMIN_BASE_URL})"
    with (
        httpx.Client(
            timeout=settings.LINK_CHECK_TIMEOUT_SECONDS,
            follow_redirects=False,
            headers={"User-Agent": user_agent},
        ) as client,
        ThreadPoolExecutor(max_workers=settings.LINK_CHECK_MAX_WORKERS) as pool,
    ):
        checker = ExternalLinkChecker(client, rate_limiter, limits)
        ordered = sorted(urls)
        return dict(zip(ordered, pool.map(checker.check, ordered), strict=True))


def _record_results(
    links_by_page: dict[Page, set[str]], results: dict[str, LinkResult]
) -> list[LinkCheck]:
    now = timezone.now()
    existing = {
        (check.url, check.source_page_id): check
        for check in LinkCheck.objects.filter(
            source_page_id__in=[page.pk for page in links_by_page]
        )
    }
    new_checks: list[LinkCheck] = []
    updated_checks: list[LinkCheck] = []
    for page, urls in links_by_page.items():
        for url in urls:
            check = existing.get((url, page.pk))
            if check is None:
                check = LinkCheck(url=url, source_page=page, failure_count=0)
                new_checks.append(check)
            else:
                updated_checks.append(check)
            _apply_result(check, results[url], now)

    LinkCheck.objects.bulk_create(new_checks)
    LinkCheck.objects.bulk_update(
        updated_checks, ["status_code", "error", "failure_count", "last_checked_at"]
    )
    current = {
        (check.url, check.source_page_id) for check in new_checks + updated_checks
    }
    stale_ids = [check.pk for key, check in existing.items() if key not in current]
    LinkCheck.objects.filter(pk__in=stale_ids).delete()
    return new_checks + updated_checks


def _apply_result(check: LinkCheck, result: LinkResult, now: datetime) -> None:
    if result.is_broken:
        check.failure_count += 1
    elif result.is_ok:
        check.failure_count = 0
    check.status_code = result.status_code
    check.error = result.error[:ERROR_MAX_LENGTH]
    check.last_checked_at = now


def _broken_link_findings(
    checks: list[LinkCheck], pages: dict[int, Page]
) -> list[DetectedFinding]:
    threshold = settings.LINK_CHECK_FAILURE_THRESHOLD
    findings = []
    for check in checks:
        if check.failure_count < threshold:
            continue
        page = pages[check.source_page_id]
        reason = f"HTTP {check.status_code}" if check.status_code else check.error
        findings.append(
            DetectedFinding(
                page=page,
                page_url=page.get_full_url() or "",
                locale_id=page.locale_id,
                data=FindingData(
                    code=BROKEN_LINK,
                    severity=Finding.Severity.ERROR,
                    message=(
                        f"Link to {check.url} has failed {check.failure_count} "
                        f"checks in a row ({reason})."
                    ),
                    fingerprint=check.url[:FINGERPRINT_MAX_LENGTH],
                ),
            )
        )
    return findings
