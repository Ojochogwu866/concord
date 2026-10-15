import pytest
from django.core.management import call_command
from wagtail.models import Page, Site

from briefs.home_content import HOME_HEADING
from briefs.models import BriefIndexPage, HomePage
from briefs.site_setup import ensure_site_structure


@pytest.mark.django_db
def test_replaces_wagtail_placeholder_with_home_page() -> None:
    structure = ensure_site_structure()

    root_children = Page.get_first_root_node().get_children()
    assert list(root_children.specific()) == [structure.home]
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
    assert HomePage.objects.count() == 1
    assert BriefIndexPage.objects.count() == 1
    assert Site.objects.count() == 1


@pytest.mark.django_db
def test_seeds_landing_content_once() -> None:
    home = ensure_site_structure().home
    assert home.heading == HOME_HEADING
    assert [block.block_type for block in home.body] == [
        "features",
        "steps",
        "latest_briefs",
        "text",
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

    home = HomePage.objects.get()
    assert f"home page {home.pk}" in capsys.readouterr().out
