import re
from collections import Counter

from django.db import connection
from django.test import Client, RequestFactory
from django.test.utils import CaptureQueriesContext

from audits.runner import run_page_audit
from briefs.site_setup import SiteStructure
from sitehealth.request_cache import cached_for_request


def test_computes_once_per_request() -> None:
    request = RequestFactory().get("/")
    calls: list[int] = []

    def compute() -> int:
        calls.append(1)
        return 42

    assert cached_for_request(request, "answer", compute) == 42
    assert cached_for_request(request, "answer", compute) == 42
    assert len(calls) == 1


def test_computes_every_time_without_a_request() -> None:
    calls: list[int] = []

    cached_for_request(None, "answer", lambda: calls.append(1))
    cached_for_request(None, "answer", lambda: calls.append(1))

    assert len(calls) == 2


def test_home_page_looks_up_shared_data_once(
    client: Client, site_structure: SiteStructure
) -> None:
    run_page_audit()
    client.get("/en/")

    with CaptureQueriesContext(connection) as queries:
        client.get("/en/")

    tables = Counter(
        match.group(1)
        for query in queries.captured_queries
        if (match := re.search(r'FROM "([a-z_]+)"', query["sql"]))
    )
    assert tables["briefs_briefindexpage"] == 1
    assert tables["audits_auditrun"] <= 2
