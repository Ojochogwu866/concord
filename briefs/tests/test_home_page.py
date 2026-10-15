import datetime
import json
import re

from django.test import Client
from wagtail.models import Locale

from briefs.models import BriefPage, HomePage
from briefs.site_setup import SiteStructure
from briefs.tests.conftest import BriefFactory


def render_home(client: Client, home: HomePage) -> str:
    response = client.get(home.url)
    assert response.status_code == 200
    return str(response.content.decode())


def test_hero_highlights_last_word_of_single_heading(
    client: Client, site_structure: SiteStructure
) -> None:
    html = render_home(client, site_structure.home)

    assert len(re.findall(r"<h1\b", html)) == 1
    assert 'This site checks its own <span class="mark">work.</span></h1>' in html


def test_hero_links_to_log_and_briefs(
    client: Client, site_structure: SiteStructure
) -> None:
    html = render_home(client, site_structure.home)

    assert 'class="button-primary" href="#inspection-log"' in html
    assert 'id="inspection-log"' in html
    assert f'class="text-link" href="{site_structure.brief_index.url}"' in html


def test_repository_link_only_shows_when_set(
    client: Client, site_structure: SiteStructure
) -> None:
    home = site_structure.home
    assert "View the source code" not in render_home(client, home)

    home.repository_url = "https://github.com/example/sitehealth"
    home.save_revision().publish()

    assert 'href="https://github.com/example/sitehealth"' in render_home(client, home)


def test_renders_every_seeded_section(
    client: Client, site_structure: SiteStructure
) -> None:
    html = render_home(client, site_structure.home)

    for heading in ("Inspection log", "Briefs"):
        assert f'<h2 class="section-heading">{heading}</h2>' in html


def test_inspection_log_shows_empty_state_before_first_run(
    client: Client, site_structure: SiteStructure
) -> None:
    html = render_home(client, site_structure.home)

    assert "No inspection has run yet." in html


def test_latest_briefs_shows_newest_three_with_h3_titles(
    client: Client, site_structure: SiteStructure, make_brief: BriefFactory
) -> None:
    for month in range(1, 5):
        make_brief(
            title=f"Brief from month {month}",
            published_date=datetime.date(2026, month, 1),
        )

    html = render_home(client, site_structure.home)

    assert "Brief from month 1" not in html
    assert html.index("Brief from month 4") < html.index("Brief from month 2")
    assert len(re.findall(r'<h3[^>]*>\s*<a [^>]*href="/briefs/', html)) == 3
    assert "All briefs" in html


def test_latest_briefs_shows_empty_state(
    client: Client, site_structure: SiteStructure
) -> None:
    html = render_home(client, site_structure.home)

    assert "No briefs have been published yet." in html


def test_latest_for_locale_excludes_other_locales(make_brief: BriefFactory) -> None:
    brief = make_brief()
    french = Locale.objects.create(language_code="fr")

    assert list(BriefPage.latest_for_locale(brief.locale_id)) == [brief]
    assert list(BriefPage.latest_for_locale(french.pk)) == []


def test_home_without_body_still_renders_hero(
    client: Client, site_structure: SiteStructure
) -> None:
    home = site_structure.home
    home.body = json.dumps([])
    home.save_revision().publish()

    html = render_home(client, home)

    assert "section-heading" not in html
    assert len(re.findall(r"<h1\b", html)) == 1
