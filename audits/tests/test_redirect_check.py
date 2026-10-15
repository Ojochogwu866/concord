from http import HTTPStatus

from django.test import Client
from wagtail.contrib.redirects.models import Redirect

from audits.checks.redirects import (
    BROKEN_TARGET,
    REDIRECT_CHAIN,
    REDIRECT_LOOP,
    check_redirects,
)
from audits.models import Finding
from audits.rendering import fetch_final_status
from audits.runner import run_page_audit
from briefs.site_setup import SiteStructure
from briefs.tests.fixtures import BriefFactory


def link_redirect(old_path: str, target: str) -> Redirect:
    return Redirect.objects.create(old_path=old_path, redirect_link=target)


def codes() -> list[tuple[str, str]]:
    return sorted((f.code, f.fingerprint) for f in check_redirects())


def test_healthy_redirects_have_no_findings(make_brief: BriefFactory) -> None:
    brief = make_brief()
    Redirect.objects.create(old_path="/en/briefs/old-slug", redirect_page=brief)
    link_redirect("/en/old-home", "/en/")
    link_redirect("/en/elsewhere", "https://www.w3.org/WAI/")

    assert check_redirects() == []


def test_reports_redirect_chain_with_every_hop(site_structure: SiteStructure) -> None:
    link_redirect("/en/a", "/en/b")
    link_redirect("/en/b", "/en/")

    findings = check_redirects()

    assert [(f.code, f.url, f.language_code) for f in findings] == [
        (REDIRECT_CHAIN, "/en/a", "en")
    ]
    assert "/en/a → /en/b → /en" in findings[0].message


def test_reports_redirect_loop(site_structure: SiteStructure) -> None:
    link_redirect("/fr/a", "/fr/b")
    link_redirect("/fr/b", "/fr/a")

    assert codes() == [(REDIRECT_LOOP, "/fr/a"), (REDIRECT_LOOP, "/fr/b")]


def test_reports_redirect_to_unpublished_page(make_brief: BriefFactory) -> None:
    brief = make_brief()
    Redirect.objects.create(old_path="/en/briefs/old-slug", redirect_page=brief)
    brief.unpublish()

    findings = check_redirects()

    assert [f.code for f in findings] == [BROKEN_TARGET]
    assert "not published" in findings[0].message


def test_reports_redirect_to_missing_path(site_structure: SiteStructure) -> None:
    link_redirect("/en/old", "/en/does-not-exist/")

    findings = check_redirects()

    assert [f.code for f in findings] == [BROKEN_TARGET]
    assert "returns HTTP 404" in findings[0].message


def test_reports_redirect_without_a_target(site_structure: SiteStructure) -> None:
    Redirect.objects.create(old_path="/en/orphan")

    assert codes() == [(BROKEN_TARGET, "/en/orphan")]


def test_run_records_redirect_findings_once_and_resolves_them(
    site_structure: SiteStructure,
) -> None:
    broken = link_redirect("/en/old", "/en/does-not-exist/")
    run_page_audit()
    run_page_audit()

    open_findings = Finding.objects.filter(code=BROKEN_TARGET, resolved_at__isnull=True)
    assert open_findings.count() == 1
    assert open_findings.get().page is None

    broken.redirect_link = "/en/"
    broken.save()
    run_page_audit()

    assert not Finding.objects.filter(resolved_at__isnull=True).exists()


def test_log_names_redirects_by_their_old_path(
    client: Client, site_structure: SiteStructure
) -> None:
    link_redirect("/en/old", "/en/does-not-exist/")
    run_page_audit()

    html = client.get("/en/").content.decode()

    assert "/en/old" in html
    assert BROKEN_TARGET in html


def test_status_check_stops_following_a_redirect_loop(
    site_structure: SiteStructure,
) -> None:
    link_redirect("/en/x", "/en/y")
    link_redirect("/en/y", "/en/x")

    assert fetch_final_status("/en/x") == HTTPStatus.LOOP_DETECTED
