import uuid
from collections import defaultdict

from bs4 import BeautifulSoup
from django.db import transaction
from wagtail.models import Locale, Page

from audits.models import AuditRun
from audits.registry import InspectedPage, registered_checks, registered_site_checks
from audits.scan import (
    DetectedFinding,
    failure_recorded,
    finish_run,
    live_pages,
    render_pages,
    sync_findings,
)


def run_page_audit() -> AuditRun:
    run = AuditRun.objects.create(kind=AuditRun.Kind.PAGES)
    with failure_recorded(run):
        pages = live_pages()
        locale_ids = dict(Locale.objects.values_list("language_code", "pk"))
        rendered, failures = render_pages(run, pages)
        translations = _live_pages_by_translation_key(pages)
        detected = [
            finding
            for item in rendered
            for finding in _inspect(
                InspectedPage(
                    page=item.page,
                    url=item.path,
                    html=BeautifulSoup(item.html, "html.parser"),
                    translations=translations[item.page.translation_key],
                ),
                locale_ids,
            )
        ]
        detected.extend(_run_site_checks(locale_ids))

        with transaction.atomic():
            open_by_code = sync_findings(run, detected, {f.page_id for f in failures})
            finish_run(run, len(pages), failures, {"open_by_code": dict(open_by_code)})
    return run


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


def _live_pages_by_translation_key(
    pages: list[Page],
) -> defaultdict[uuid.UUID, dict[str, Page]]:
    index: defaultdict[uuid.UUID, dict[str, Page]] = defaultdict(dict)
    for page in pages:
        index[page.translation_key][page.locale.language_code] = page
    return index
