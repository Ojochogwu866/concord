from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from wagtail.models import Page

from audits.checks.accessibility import (
    EMPTY_LINK,
    HEADING_SKIP,
    IMAGE_ALT,
    LANGUAGE_MISMATCH,
    MISSING_LABEL,
    check_document_language,
    check_form_labels,
    check_heading_order,
    check_image_alt_text,
    check_link_text,
)
from audits.registry import Check, InspectedPage, registered_checks
from briefs.site_setup import SiteStructure

FIXTURES = Path(__file__).parent / "fixtures"
ACCESSIBILITY_CHECKS = [
    check_heading_order,
    check_image_alt_text,
    check_link_text,
    check_form_labels,
    check_document_language,
]


@pytest.fixture
def english_page(site_structure: SiteStructure) -> Page:
    return site_structure.home


def inspect_html(html: str, page: Page) -> InspectedPage:
    return InspectedPage(
        page=page, url=page.url, html=BeautifulSoup(html, "html.parser")
    )


def inspect_fixture(name: str, page: Page) -> InspectedPage:
    return inspect_html((FIXTURES / name).read_text(), page)


def test_every_accessibility_check_is_registered() -> None:
    assert set(ACCESSIBILITY_CHECKS) <= set(registered_checks())


@pytest.mark.parametrize("check", ACCESSIBILITY_CHECKS)
def test_accessible_page_has_no_findings(check: Check, english_page: Page) -> None:
    assert check(inspect_fixture("accessible_page.html", english_page)) == []


def test_reports_skipped_heading_level(english_page: Page) -> None:
    findings = check_heading_order(
        inspect_fixture("inaccessible_page.html", english_page)
    )

    assert [finding.code for finding in findings] == [HEADING_SKIP]
    assert "h1 to h4" in findings[0].message


def test_reports_image_without_alt_attribute(english_page: Page) -> None:
    findings = check_image_alt_text(
        inspect_fixture("inaccessible_page.html", english_page)
    )

    assert [(f.code, f.fingerprint) for f in findings] == [
        (IMAGE_ALT, "/media/battery.jpg")
    ]


def test_reports_links_without_accessible_name(english_page: Page) -> None:
    findings = check_link_text(inspect_fixture("inaccessible_page.html", english_page))

    assert {f.fingerprint for f in findings} == {"/en/briefs/", "/en/"}
    assert {f.code for f in findings} == {EMPTY_LINK}


def test_reports_unlabelled_form_controls(english_page: Page) -> None:
    findings = check_form_labels(
        inspect_fixture("inaccessible_page.html", english_page)
    )

    assert {f.fingerprint for f in findings} == {"input:email", "select:topic"}
    assert {f.code for f in findings} == {MISSING_LABEL}


def test_reports_document_language_mismatch(english_page: Page) -> None:
    findings = check_document_language(
        inspect_fixture("inaccessible_page.html", english_page)
    )

    assert [f.code for f in findings] == [LANGUAGE_MISMATCH]
    assert "“fr”" in findings[0].message


def test_reports_missing_document_language(english_page: Page) -> None:
    findings = check_document_language(inspect_html("<p>No html tag</p>", english_page))

    assert [f.code for f in findings] == [LANGUAGE_MISMATCH]


def test_accepts_regional_language_subtag(english_page: Page) -> None:
    html = '<html lang="en-GB"><body></body></html>'

    assert check_document_language(inspect_html(html, english_page)) == []


def test_tolerates_malformed_html(english_page: Page) -> None:
    findings = check_heading_order(
        inspect_html("<h1>Unclosed<h3>Skipped <img src=x>", english_page)
    )

    assert [f.code for f in findings] == [HEADING_SKIP]
