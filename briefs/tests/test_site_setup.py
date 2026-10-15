import pytest
from django.conf import settings
from django.core.management import call_command
from pytest_django.fixtures import Settings
from wagtail.models import Locale, Page, Site

from briefs.home_content import (
    FRENCH_TRANSLATIONS,
    HOME_HEADING,
    HOME_LEAD,
    INSPECTION_LOG_NOTE,
    LATEST_BRIEFS_NOTE,
)
from briefs.models import BriefIndexPage, HomePage
from briefs.site_setup import SiteStructure, ensure_site_structure


@pytest.mark.django_db
def test_replaces_wagtail_placeholder_with_home_page() -> None:
    structure = ensure_site_structure()

    root_children = Page.get_first_root_node().get_children().specific()
    assert structure.home in root_children
    assert all(isinstance(page, HomePage) for page in root_children)
    assert Site.objects.get(is_default_site=True).root_page_id == structure.home.pk
    assert structure.home.live
    assert structure.brief_index.get_parent().pk == structure.home.pk
    assert structure.brief_index.live


@pytest.mark.django_db
def test_is_idempotent() -> None:
    first = ensure_site_structure()
    second = ensure_site_structure()

    assert second.home.pk == first.home.pk
    assert second.brief_index.pk == first.brief_index.pk
    assert HomePage.objects.count() == len(settings.WAGTAIL_CONTENT_LANGUAGES)
    assert BriefIndexPage.objects.count() == len(settings.WAGTAIL_CONTENT_LANGUAGES)
    assert Site.objects.count() == 1


@pytest.mark.django_db
def test_seeds_landing_content_once() -> None:
    home = ensure_site_structure().home
    assert home.heading == HOME_HEADING
    assert [block.block_type for block in home.body] == [
        "inspection_log",
        "latest_briefs",
    ]

    home.heading = "Edited by an editor"
    home.save_revision().publish()
    ensure_site_structure()

    home.refresh_from_db()
    assert home.heading == "Edited by an editor"


@pytest.mark.django_db
def test_keeps_editor_pages_under_root() -> None:
    editor_page = Page(title="Editor draft", slug="editor-draft")
    Page.get_first_root_node().add_child(instance=editor_page)
    editor_page.add_child(instance=Page(title="Child", slug="child"))

    ensure_site_structure()

    assert Page.objects.filter(pk=editor_page.pk).exists()


@pytest.mark.django_db
def test_command_reports_created_pages(capsys: pytest.CaptureFixture[str]) -> None:
    call_command("bootstrap_site")

    home = HomePage.objects.get(locale=Locale.get_default())
    assert f"home page {home.pk}" in capsys.readouterr().out


def test_publishes_french_home_and_index_with_french_copy(
    site_structure: SiteStructure,
) -> None:
    structure = site_structure
    french = Locale.objects.get(language_code="fr")

    home = structure.home.get_translation(french)
    brief_index = structure.brief_index.get_translation(french)

    assert home.live and brief_index.live
    assert home.heading == "Ce site vérifie son propre travail."
    assert brief_index.title == "Notes"
    assert brief_index.url == "/fr/notes/"
    assert brief_index.get_parent().pk == home.pk


def test_french_seed_covers_every_translatable_string() -> None:
    english_strings = {
        HOME_HEADING,
        HOME_LEAD,
        INSPECTION_LOG_NOTE,
        LATEST_BRIEFS_NOTE,
        "Site Health",
        "home",
        "Inspection log",
        "Briefs",
        "briefs",
    }

    assert english_strings <= FRENCH_TRANSLATIONS.keys()


@pytest.mark.django_db
def test_site_address_follows_admin_base_url(settings: Settings) -> None:
    settings.WAGTAILADMIN_BASE_URL = "https://health.example.com"
    ensure_site_structure()

    site = Site.objects.get(is_default_site=True)
    assert (site.hostname, site.port) == ("health.example.com", 443)

    settings.WAGTAILADMIN_BASE_URL = "http://localhost:8000"
    ensure_site_structure()

    site.refresh_from_db()
    assert (site.hostname, site.port) == ("localhost", 8000)
