from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from django.conf import settings
from wagtail.models import Page

from audits.checks.seo import (
    H1_COUNT,
    LONG_DESCRIPTION,
    LONG_TITLE,
    MISSING_CANONICAL,
    MISSING_DESCRIPTION,
    MISSING_HREFLANG,
    check_canonical,
    check_h1_count,
    check_hreflang,
    check_meta_description,
    check_title_length,
)
from audits.registry import Check, InspectedPage, registered_checks
from briefs.site_setup import SiteStructure

FIXTURES = Path(__file__).parent / "fixtures"
SEO_CHECKS = [
    check_title_length,
    check_meta_description,
    check_canonical,
    check_hreflang,
    check_h1_count,
]


@pytest.fixture
def translations(site_structure: SiteStructure) -> dict[str, Page]:
    home = site_structure.home
    return {
        page.locale.language_code: page
        for page in home.get_translations(inclusive=True)
    }


def inspect(name: str, translations: dict[str, Page]) -> InspectedPage:
    html = BeautifulSoup((FIXTURES / name).read_text(), "html.parser")
    return InspectedPage(
        page=translations["en"], url="/en/", html=html, translations=translations
    )


def codes(check: Check, name: str, translations: dict[str, Page]) -> list[str]:
    return sorted(f.code for f in check(inspect(name, translations)))


def test_every_seo_check_is_registered() -> None:
    assert set(SEO_CHECKS) <= set(registered_checks())


@pytest.mark.parametrize("check", SEO_CHECKS)
def test_well_formed_page_has_no_findings(
    check: Check, translations: dict[str, Page]
) -> None:
    assert codes(check, "seo_page.html", translations) == []


def test_reports_title_longer_than_the_limit(translations: dict[str, Page]) -> None:
    findings = check_title_length(inspect("seo_problems.html", translations))

    assert [f.code for f in findings] == [LONG_TITLE]
    assert f"after about {settings.SEO_TITLE_MAX_LENGTH}" in findings[0].message


def test_reports_description_longer_than_the_limit(
    translations: dict[str, Page],
) -> None:
    assert codes(check_meta_description, "seo_problems.html", translations) == [
        LONG_DESCRIPTION
    ]


def test_reports_missing_description_and_canonical(
    translations: dict[str, Page],
) -> None:
    html = BeautifulSoup("<html><head><title>T</title></head></html>", "html.parser")
    inspected = InspectedPage(page=translations["en"], url="/en/", html=html)

    assert [f.code for f in check_meta_description(inspected)] == [MISSING_DESCRIPTION]
    assert [f.code for f in check_canonical(inspected)] == [MISSING_CANONICAL]


def test_reports_each_missing_hreflang_alternate(
    translations: dict[str, Page],
) -> None:
    findings = check_hreflang(inspect("seo_problems.html", translations))

    assert [(f.code, f.fingerprint) for f in findings] == [
        (MISSING_HREFLANG, "fr"),
        (MISSING_HREFLANG, "x-default"),
    ]


def test_skips_hreflang_for_untranslated_pages(translations: dict[str, Page]) -> None:
    html = BeautifulSoup("<html><head></head></html>", "html.parser")
    inspected = InspectedPage(
        page=translations["en"],
        url="/en/",
        html=html,
        translations={"en": translations["en"]},
    )

    assert check_hreflang(inspected) == []


def test_reports_more_than_one_h1(translations: dict[str, Page]) -> None:
    findings = check_h1_count(inspect("seo_problems.html", translations))

    assert [f.code for f in findings] == [H1_COUNT]
    assert "2 main headings" in findings[0].message


def test_reports_page_without_h1(translations: dict[str, Page]) -> None:
    html = BeautifulSoup("<main><h2>No main heading</h2></main>", "html.parser")
    inspected = InspectedPage(page=translations["en"], url="/en/", html=html)

    assert [f.code for f in check_h1_count(inspected)] == [H1_COUNT]
