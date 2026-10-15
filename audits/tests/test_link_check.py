import json
import socket
from collections.abc import Iterator

import pytest
import respx
from django.core.management import call_command
from pytest_django.fixtures import Settings

from audits.checks.translations import MISSING_TRANSLATION
from audits.links import BROKEN_LINK, extract_links, run_link_check
from audits.models import Finding, LinkCheck
from audits.runner import run_page_audit
from briefs.models import BriefPage
from briefs.tests.fixtures import BriefFactory

DEAD_LINK = "https://public.example/gone"


@pytest.fixture(autouse=True)
def quiet_settings(settings: Settings) -> None:
    settings.DESIGNER_PROFILE_URL = ""
    settings.LINK_CHECK_RETRY_BACKOFF_SECONDS = 0
    settings.LINK_CHECK_HOST_INTERVAL_SECONDS = 0


@pytest.fixture(autouse=True)
def fake_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    def getaddrinfo(
        host: str, port: int | None, *args: object
    ) -> list[tuple[object, ...]]:
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]

    monkeypatch.setattr("audits.http.socket.getaddrinfo", getaddrinfo)


@pytest.fixture
def network() -> Iterator[respx.MockRouter]:
    with respx.mock(assert_all_called=False) as router:
        yield router


def body_linking_to(*urls: str) -> str:
    links = " ".join(f'<a href="{url}">source</a>' for url in urls)
    return json.dumps([{"type": "paragraph", "value": f"<p>{links}</p>"}])


def open_link_findings() -> list[Finding]:
    return list(Finding.objects.filter(code=BROKEN_LINK, resolved_at__isnull=True))


def test_extracts_absolute_http_links_without_fragments() -> None:
    html = """
        <a href="/en/briefs/#top">relative</a>
        <a href="https://public.example/page#section">absolute</a>
        <a href="#main">fragment only</a>
        <a href="mailto:dd@example.com">email</a>
        <a href="tel:+33100000000">phone</a>
        <a href="javascript:void(0)">script</a>
        <a href="ftp://public.example/file">ftp</a>
    """

    assert extract_links(html, "http://localhost:8000/en/") == {
        "http://localhost:8000/en/briefs/",
        "https://public.example/page",
    }


def test_reports_a_dead_link_only_after_three_failures(
    make_brief: BriefFactory, network: respx.MockRouter
) -> None:
    brief = make_brief(body=body_linking_to(DEAD_LINK))
    network.head(DEAD_LINK).respond(404)

    run_link_check()
    run_link_check()
    assert open_link_findings() == []
    assert LinkCheck.objects.get(url=DEAD_LINK).failure_count == 2

    run_link_check()

    finding = open_link_findings()[0]
    assert finding.page_id == brief.pk
    assert finding.fingerprint == DEAD_LINK
    assert "failed 3 checks in a row (HTTP 404)" in finding.message


def test_a_success_resets_the_failure_count(
    make_brief: BriefFactory, network: respx.MockRouter
) -> None:
    make_brief(body=body_linking_to(DEAD_LINK))
    route = network.head(DEAD_LINK)
    route.respond(404)
    run_link_check()
    run_link_check()

    route.respond(200)
    run_link_check()

    assert LinkCheck.objects.get(url=DEAD_LINK).failure_count == 0
    assert open_link_findings() == []


def test_bot_protection_neither_counts_nor_resets(
    make_brief: BriefFactory, network: respx.MockRouter
) -> None:
    make_brief(body=body_linking_to(DEAD_LINK))
    route = network.head(DEAD_LINK)
    route.respond(404)
    run_link_check()

    route.respond(403)
    run_link_check()

    check = LinkCheck.objects.get(url=DEAD_LINK)
    assert (check.failure_count, check.status_code) == (1, 403)


def test_broken_internal_links_count_without_network(make_brief: BriefFactory) -> None:
    make_brief(body=body_linking_to("/en/briefs/does-not-exist/"))

    for _ in range(3):
        run_link_check()

    assert [f.fingerprint for f in open_link_findings()] == [
        "http://localhost:8000/en/briefs/does-not-exist/"
    ]


def test_removing_a_link_clears_its_history_and_finding(
    make_brief: BriefFactory, network: respx.MockRouter
) -> None:
    brief = make_brief(body=body_linking_to(DEAD_LINK))
    network.head(DEAD_LINK).respond(404)
    for _ in range(3):
        run_link_check()

    brief.body = body_linking_to()
    brief.save_revision().publish()
    run_link_check()

    assert not LinkCheck.objects.filter(url=DEAD_LINK).exists()
    assert open_link_findings() == []


def test_page_audits_and_link_checks_leave_each_others_findings_alone(
    make_brief: BriefFactory, network: respx.MockRouter
) -> None:
    make_brief(body=body_linking_to(DEAD_LINK))
    network.head(DEAD_LINK).respond(404)
    run_page_audit()
    for _ in range(3):
        run_link_check()

    run_page_audit()
    run_link_check()

    open_codes = set(
        Finding.objects.filter(resolved_at__isnull=True).values_list("code", flat=True)
    )
    assert {BROKEN_LINK, MISSING_TRANSLATION} <= open_codes


def test_command_reports_links_checked(
    make_brief: BriefFactory,
    network: respx.MockRouter,
    capsys: pytest.CaptureFixture[str],
) -> None:
    make_brief(body=body_linking_to(DEAD_LINK))
    network.head(DEAD_LINK).respond(404)

    call_command("check_links")

    output = capsys.readouterr().out
    assert "1 failing now" in output
    assert BriefPage.objects.exists()
