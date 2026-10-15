from django import template
from django.template import Context
from wagtail.models import Site

from briefs.models import BriefIndexPage

register = template.Library()


@register.filter
def split_last_word(text: str) -> tuple[str, str]:
    leading, _, last = text.strip().rpartition(" ")
    return leading, last


@register.simple_tag(takes_context=True)
def brief_index_page(context: Context) -> BriefIndexPage | None:
    request = context.get("request")
    site = Site.find_for_request(request) if request else None
    if site is None:
        return None
    brief_index: BriefIndexPage | None = (
        BriefIndexPage.objects.child_of(site.root_page).live().first()
    )
    return brief_index
