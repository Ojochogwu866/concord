import json
from dataclasses import dataclass

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from wagtail.models import Locale, Page, Site
from wagtail_localize.models import Translation, TranslationSource

from briefs.home_content import (
    FRENCH_TRANSLATIONS,
    HOME_BODY,
    HOME_HEADING,
    HOME_LEAD,
)
from briefs.models import BriefIndexPage, HomePage

SITE_NAME = "Site Health"
DEFAULT_SITE_HOSTNAME = "localhost"
DEFAULT_SITE_PORT = 80
HOME_TITLE = "Site Health"
HOME_SLUG = "home"
BRIEF_INDEX_TITLE = "Briefs"
BRIEF_INDEX_SLUG = "briefs"
SEED_TRANSLATIONS = {"fr": FRENCH_TRANSLATIONS}


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
            _ensure_translation(page, locale, strings)
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
    site = Site.objects.filter(is_default_site=True).first()
    if site is None:
        return Site.objects.create(
            hostname=DEFAULT_SITE_HOSTNAME,
            port=DEFAULT_SITE_PORT,
            root_page=home,
            site_name=SITE_NAME,
            is_default_site=True,
        )
    if site.root_page_id != home.pk:
        site.root_page = home
        site.save(update_fields=["root_page"])
    return site


def _ensure_brief_index(home: HomePage) -> BriefIndexPage:
    existing: BriefIndexPage | None = BriefIndexPage.objects.child_of(home).first()
    if existing is not None:
        return existing
    brief_index = BriefIndexPage(title=BRIEF_INDEX_TITLE, slug=BRIEF_INDEX_SLUG)
    home.add_child(instance=brief_index)
    brief_index.save_revision().publish()
    return brief_index


def _ensure_translation(page: Page, locale: Locale, strings: dict[str, str]) -> None:
    if page.has_translation(locale):
        return
    source, _ = TranslationSource.get_or_create_from_instance(page)
    translation, _ = Translation.objects.get_or_create(
        source=source, target_locale=locale
    )
    po_file = translation.export_po()
    for entry in po_file:
        entry.msgstr = strings[entry.msgid]
    translation.import_po(po_file)
    # wagtail-localize defers publishing to commit, when the queued revision is stale
    # and would reset the parent's child count, so save a draft and publish it now.
    translation.save_target(publish=False)
    translation.get_target_instance().get_latest_revision().publish()
