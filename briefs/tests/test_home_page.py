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


def test_hero_has_single_heading_and_primary_action(
    client: Client, site_structure: SiteStructure
) -> None:
    html = render_home(client, site_structure.home)

    assert len(re.findall(r"<h1\b", html)) == 1
    assert "A bilingual Wagtail site that audits itself" in html
    assert f'class="button-primary" href="{site_structure.brief_index.url}"' in html


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

    for heading in ("What it checks", "How it works", "Sample briefs", "Built with"):
        assert f'<h2 class="section-heading">{heading}</h2>' in html
    assert '<code class="code-label">i18n.*</code>' in html


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
    assert len(re.findall(r'<h3 class="text-xl', html)) == 3
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
