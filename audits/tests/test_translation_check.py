from bs4 import BeautifulSoup
from wagtail.models import Locale, Page

from audits.checks.translations import (
    MISSING_TRANSLATION,
    STALE_TRANSLATION,
    check_translations,
)
from audits.registry import FindingData, InspectedPage
from briefs.models import BriefPage
from briefs.tests.fixtures import BriefFactory


def run_check(page: Page) -> list[FindingData]:
    translations = {
        translation.locale.language_code: translation
        for translation in page.get_translations(inclusive=True).live()
    }
    inspected = InspectedPage(
        page=page,
        url=page.url,
        html=BeautifulSoup("", "html.parser"),
        translations=translations,
    )
    return check_translations(inspected)


def translate(brief: BriefPage) -> BriefPage:
    translation: BriefPage = brief.copy_for_translation(
        Locale.objects.get(language_code="fr")
    )
    translation.save_revision().publish()
    published: BriefPage = BriefPage.objects.get(pk=translation.pk)
    return published


def test_reports_missing_french_version(make_brief: BriefFactory) -> None:
    findings = run_check(make_brief())

    assert [(f.code, f.language_code) for f in findings] == [
        (MISSING_TRANSLATION, "fr")
    ]
    assert findings[0].message == "No French version of this page is published."


def test_unpublished_translation_still_counts_as_missing(
    make_brief: BriefFactory,
) -> None:
    brief = make_brief()
    translate(brief).unpublish()

    assert [f.code for f in run_check(brief)] == [MISSING_TRANSLATION]


def test_up_to_date_translation_has_no_findings(make_brief: BriefFactory) -> None:
    brief = make_brief()
    translate(brief)

    assert run_check(brief) == []


def test_reports_translation_older_than_its_source(make_brief: BriefFactory) -> None:
    brief = make_brief()
    translate(brief)
    brief.save_revision().publish()

    findings = run_check(BriefPage.objects.get(pk=brief.pk))

    assert [(f.code, f.language_code) for f in findings] == [(STALE_TRANSLATION, "fr")]


def test_ignores_pages_in_other_languages(make_brief: BriefFactory) -> None:
    translation = translate(make_brief())

    assert run_check(translation) == []
