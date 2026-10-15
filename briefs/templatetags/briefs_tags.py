from dataclasses import dataclass

from django import template
from django.conf import settings
from django.http import HttpRequest
from django.template import Context
from django.utils.translation import get_language
from wagtail.models import Page, Site

from briefs.models import BriefIndexPage

register = template.Library()


@dataclass(frozen=True)
class LanguageLink:
    code: str
    name: str
    url: str
    absolute_url: str
    is_current: bool
    has_translation: bool


@register.filter
def split_last_word(text: str) -> tuple[str, str]:
    leading, _, last = text.strip().rpartition(" ")
    return leading, last


@register.simple_tag(takes_context=True)
def brief_index_page(context: Context) -> BriefIndexPage | None:
    site = _site_for(context)
    if site is None:
        return None
    brief_index: BriefIndexPage | None = (
        BriefIndexPage.objects.child_of(site.root_page).live().first()
    )
    return brief_index.localized if brief_index else None


@register.simple_tag(takes_context=True)
def localized_home_url(context: Context) -> str:
    site = _site_for(context)
    if site is None:
        return "/"
    url: str = site.root_page.localized.url
    return url


@register.simple_tag(takes_context=True)
def language_links(context: Context) -> list[LanguageLink]:
    request: HttpRequest | None = context.get("request")
    site = _site_for(context)
    if request is None or site is None:
        return []

    page = context.get("page")
    page_translations = _live_translations(page) if isinstance(page, Page) else {}
    home_translations = _live_translations(site.root_page)
    current_language = get_language()

    links = []
    for code, name in settings.WAGTAIL_CONTENT_LANGUAGES:
        target = page_translations.get(code) or home_translations.get(code)
        url = target.url if target else f"/{code}/"
        links.append(
            LanguageLink(
                code=code,
                name=name,
                url=url,
                absolute_url=request.build_absolute_uri(url),
                is_current=code == current_language,
                has_translation=code in page_translations,
            )
        )
    return links


def _site_for(context: Context) -> Site | None:
    request = context.get("request")
    site: Site | None = Site.find_for_request(request) if request else None
    return site


def _live_translations(page: Page) -> dict[str, Page]:
    translations = page.get_translations(inclusive=True).live().select_related("locale")
    return {
        translation.locale.language_code: translation for translation in translations
    }
