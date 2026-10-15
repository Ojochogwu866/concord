import re

import pytest
from django.test import Client
from wagtail.models import Locale

from briefs.forms import BriefPageForm
from briefs.models import BriefPage, Topic
from briefs.site_setup import SiteStructure
from briefs.tests.conftest import BriefFactory


@pytest.fixture
def french(site_structure: SiteStructure) -> Locale:
    return Locale.objects.get(language_code="fr")


def translate_brief(brief: BriefPage, locale: Locale) -> BriefPage:
    translation: BriefPage = brief.copy_for_translation(locale)
    translation.title = f"FR {brief.title}"
    translation.save_revision().publish()
    return translation


def language_link(html: str, code: str) -> str:
    match = re.search(
        rf'<a class="lang-link[^"]*" href="([^"]+)" hreflang="{code}"', html
    )
    assert match, f"no {code} language link"
    return match.group(1)


def test_switcher_links_home_pages_to_each_other(
    client: Client, site_structure: SiteStructure
) -> None:
    html = client.get("/en/").content.decode()

    assert language_link(html, "en") == "/en/"
    assert language_link(html, "fr") == "/fr/"
    assert 'href="/en/" hreflang="en" aria-current="true">' in html
    assert 'href="/fr/" hreflang="fr" aria-current' not in html


def test_switcher_links_to_translated_brief(
    client: Client, make_brief: BriefFactory, french: Locale
) -> None:
    brief = make_brief(title="Grid storage")
    translate_brief(brief, french)

    html = client.get(brief.url).content.decode()

    assert language_link(html, "fr") == "/fr/notes/grid-storage/"
    assert 'hreflang="fr" href="http://testserver/fr/notes/grid-storage/"' in html


def test_switcher_falls_back_to_home_when_brief_is_untranslated(
    client: Client, make_brief: BriefFactory, french: Locale
) -> None:
    brief = make_brief(title="Grid storage")

    html = client.get(brief.url).content.decode()

    assert language_link(html, "fr") == "/fr/"
    assert "lang-link-fallback" in html
    assert 'rel="alternate" hreflang="fr"' not in html
    assert 'rel="alternate" hreflang="x-default"' in html


def test_french_briefs_index_is_routable(
    client: Client, site_structure: SiteStructure
) -> None:
    response = client.get("/fr/notes/")

    assert response.status_code == 200
    assert '<h1 class="page-heading mt-5">Notes</h1>' in response.content.decode()


def test_french_pages_use_french_language_and_navigation(
    client: Client, site_structure: SiteStructure
) -> None:
    html = client.get("/fr/").content.decode()

    assert '<html lang="fr">' in html
    assert 'href="/fr/notes/"' in html
    assert "Ce site vérifie son propre" in html
    assert "Aller au contenu principal" in html


def test_french_home_lists_only_french_briefs(
    client: Client, make_brief: BriefFactory, french: Locale
) -> None:
    english_only = make_brief(title="English only brief")
    translated = make_brief(title="Translated brief")
    translate_brief(translated, french)

    html = client.get("/fr/").content.decode()

    assert "FR Translated brief" in html
    assert english_only.title not in html


def test_brief_form_only_offers_topics_in_the_brief_language(
    make_brief: BriefFactory, french: Locale
) -> None:
    english_topic = Topic.objects.create(name="Energy", slug="energy")
    french_topic = Topic.objects.create(name="Énergie", slug="energie", locale=french)
    brief = make_brief()

    form_class = BriefPage.get_edit_handler().get_form_class()
    form = form_class(instance=brief, for_user=None)

    assert isinstance(form, BriefPageForm)
    assert list(form.fields["topics"].queryset) == [english_topic]
    assert french_topic not in form.fields["topics"].queryset


def test_translated_brief_switches_to_topics_in_its_own_language(
    make_brief: BriefFactory, french: Locale
) -> None:
    english_topic = Topic.objects.create(name="Energy", slug="energy")
    french_topic = english_topic.copy_for_translation(french)
    french_topic.name = "Énergie"
    french_topic.save()
    untranslated_topic = Topic.objects.create(name="Housing", slug="housing")
    brief = make_brief(topics=[english_topic, untranslated_topic])

    translation = translate_brief(brief, french)

    translation.refresh_from_db()
    assert set(translation.topics.all()) == {french_topic, untranslated_topic}


def test_french_brief_page_hides_topics_without_a_french_version(
    client: Client, make_brief: BriefFactory, french: Locale
) -> None:
    untranslated_topic = Topic.objects.create(name="Housing", slug="housing")
    brief = make_brief(topics=[untranslated_topic])
    translation = translate_brief(brief, french)

    html = client.get(translation.url).content.decode()

    assert "?topic=housing" not in html
