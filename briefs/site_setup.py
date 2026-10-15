import json
from dataclasses import dataclass
from urllib.parse import urlsplit

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from wagtail.models import Locale, Page, Site

from briefs.home_content import (
    BRIEF_INDEX_INTRO,
    FRENCH_BRIEF_INDEX_INTRO,
    FRENCH_TRANSLATIONS,
    HOME_BODY,
    HOME_HEADING,
    HOME_LEAD,
)
from briefs.models import BriefIndexPage, HomePage
from briefs.translation import ensure_translation

SITE_NAME = "Concord"
FALLBACK_HOSTNAME = "localhost"
HTTP_PORT = 80
HTTPS_PORT = 443
HOME_TITLE = "Concord"
HOME_SLUG = "home"
BRIEF_INDEX_TITLE = "Briefs"
BRIEF_INDEX_SLUG = "briefs"
SEED_TRANSLATIONS = {"fr": FRENCH_TRANSLATIONS}
SEED_INDEX_INTROS = {"en": BRIEF_INDEX_INTRO, "fr": FRENCH_BRIEF_INDEX_INTRO}


@dataclass(frozen=True)
class SiteStructure:
    site: Site
    home: HomePage
    brief_index: BriefIndexPage


@transaction.atomic
def ensure_site_structure() -> SiteStructure:
    home = _ensure_home_page()
    _ensure_home_content(home)
    site = _ensure_default_site(home)
    brief_index = _ensure_brief_index(home)
    for language_code, strings in SEED_TRANSLATIONS.items():
        locale, _ = Locale.objects.get_or_create(language_code=language_code)
        for page in (home, brief_index):
            ensure_translation(page, locale, strings)
    _ensure_index_intros(brief_index)
    return SiteStructure(site=site, home=home, brief_index=brief_index)


def _ensure_home_page() -> HomePage:
    existing: HomePage | None = HomePage.objects.filter(
        locale=Locale.get_default()
    ).first()
    if existing is not None:
        return existing
    root = Page.get_first_root_node()
    _delete_placeholder_pages(root)
    home = HomePage(title=HOME_TITLE, slug=HOME_SLUG, **_initial_home_content())
    root.add_child(instance=home)
    home.save_revision().publish()
    return home


def _ensure_home_content(home: HomePage) -> None:
    if home.heading:
        return
    for field, value in _initial_home_content().items():
        setattr(home, field, value)
    home.save_revision().publish()


def _initial_home_content() -> dict[str, str]:
    return {"heading": HOME_HEADING, "lead": HOME_LEAD, "body": json.dumps(HOME_BODY)}


def _delete_placeholder_pages(root: Page) -> None:
    # Wagtail's install migration creates a plain "Welcome" page with no template.
    base_page_type = ContentType.objects.get_for_model(Page)
    for page in root.get_children().filter(content_type=base_page_type):
        if page.is_leaf():
            page.delete()


def _ensure_default_site(home: HomePage) -> Site:
    hostname, port = _public_address()
    site = Site.objects.filter(is_default_site=True).first()
    if site is None:
        return Site.objects.create(
            hostname=hostname,
            port=port,
            root_page=home,
            site_name=SITE_NAME,
            is_default_site=True,
        )
    current = (site.root_page_id, site.hostname, site.port, site.site_name)
    if current != (home.pk, hostname, port, SITE_NAME):
        site.root_page = home
        site.hostname = hostname
        site.port = port
        site.site_name = SITE_NAME
        site.save(update_fields=["root_page", "hostname", "port", "site_name"])
    return site


def _public_address() -> tuple[str, int]:
    url = urlsplit(settings.WAGTAILADMIN_BASE_URL)
    default_port = HTTPS_PORT if url.scheme == "https" else HTTP_PORT
    return url.hostname or FALLBACK_HOSTNAME, url.port or default_port


def _ensure_index_intros(brief_index: BriefIndexPage) -> None:
    # Source language first, so translations are never older than their source.
    for index in sorted(
        brief_index.get_translations(inclusive=True).live().specific(),
        key=lambda page: page.locale_id != brief_index.locale_id,
    ):
        intro = SEED_INDEX_INTROS.get(index.locale.language_code)
        if intro and not index.intro:
            index.intro = intro
            index.save_revision().publish()


def _ensure_brief_index(home: HomePage) -> BriefIndexPage:
    existing: BriefIndexPage | None = BriefIndexPage.objects.child_of(home).first()
    if existing is not None:
        return existing
    brief_index = BriefIndexPage(title=BRIEF_INDEX_TITLE, slug=BRIEF_INDEX_SLUG)
    home.add_child(instance=brief_index)
    brief_index.save_revision().publish()
    return brief_index
