import pytest
from django.core.management import call_command
from django.test import Client
from wagtail.models import Locale

from briefs.demo import ensure_demo_content
from briefs.demo_content import DEMO_BRIEFS, TRANSLATED_BRIEF_SLUGS
from briefs.models import BriefPage, Topic
from briefs.site_setup import SiteStructure
from briefs.translation import MissingTranslationError, ensure_translation


@pytest.fixture
def french(site_structure: SiteStructure) -> Locale:
    return Locale.objects.get(language_code="fr")


@pytest.fixture
def demo_briefs(site_structure: SiteStructure) -> list[BriefPage]:
    return ensure_demo_content(site_structure.brief_index)


def test_creates_every_demo_brief_live_with_topics(
    demo_briefs: list[BriefPage],
) -> None:
    assert [brief.slug for brief in demo_briefs] == [d["slug"] for d in DEMO_BRIEFS]
    for brief in demo_briefs:
        assert brief.live
        assert brief.topics.exists()


def test_translates_only_the_chosen_briefs(
    demo_briefs: list[BriefPage], french: Locale
) -> None:
    translated = {brief.slug for brief in demo_briefs if brief.has_translation(french)}

    assert translated == set(TRANSLATED_BRIEF_SLUGS)
    assert not BriefPage.objects.get(slug="link-rot").has_translation(french)


def test_french_brief_uses_french_copy_and_french_topics(
    demo_briefs: list[BriefPage], french: Locale
) -> None:
    english = BriefPage.objects.get(slug="what-changed-in-wcag-2-2")
    translation = english.get_translation(french)

    assert translation.live
    assert translation.title == "Ce qui change avec les WCAG 2.2"
    assert translation.url == "/fr/notes/ce-qui-change-avec-wcag-2-2/"
    assert [topic.name for topic in translation.topics.all()] == ["Accessibilité"]


def test_french_brief_keeps_link_targets(
    client: Client, demo_briefs: list[BriefPage]
) -> None:
    html = client.get("/fr/notes/ce-qui-change-avec-wcag-2-2/").content.decode()

    assert 'href="https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/"' in html
    assert "Les nouveaux critères de niveau AA" in html


def test_is_idempotent(
    site_structure: SiteStructure, demo_briefs: list[BriefPage]
) -> None:
    ensure_demo_content(site_structure.brief_index)

    assert BriefPage.objects.count() == len(DEMO_BRIEFS) + len(TRANSLATED_BRIEF_SLUGS)
    assert (
        Topic.objects.count()
        == 2 * Topic.objects.filter(locale__language_code="en").count()
    )


def test_missing_string_names_the_untranslated_text(
    site_structure: SiteStructure, french: Locale
) -> None:
    topic = Topic.objects.create(name="Untranslated", slug="untranslated")

    with pytest.raises(MissingTranslationError, match="'Untranslated'"):
        ensure_translation(topic, french, {})


@pytest.mark.django_db
def test_command_seeds_site_and_reports(capsys: pytest.CaptureFixture[str]) -> None:
    call_command("seed_demo_content")

    assert f"{len(DEMO_BRIEFS)} briefs" in capsys.readouterr().out
    assert BriefPage.objects.filter(locale__language_code="en").count() == len(
        DEMO_BRIEFS
    )
