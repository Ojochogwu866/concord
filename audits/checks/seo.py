from bs4 import Tag
from django.conf import settings

from audits.models import Finding
from audits.registry import FindingData, InspectedPage, register_check

MISSING_DESCRIPTION = "seo.missing_description"
LONG_DESCRIPTION = "seo.long_description"
LONG_TITLE = "seo.long_title"
MISSING_CANONICAL = "seo.missing_canonical"
MISSING_HREFLANG = "seo.missing_hreflang"
H1_COUNT = "seo.h1_count"

X_DEFAULT = "x-default"


@register_check
def check_title_length(inspected: InspectedPage) -> list[FindingData]:
    title_tag = inspected.html.find("title")
    title = title_tag.get_text(" ", strip=True) if isinstance(title_tag, Tag) else ""
    limit = settings.SEO_TITLE_MAX_LENGTH
    if len(title) <= limit:
        return []
    return [
        FindingData(
            code=LONG_TITLE,
            severity=Finding.Severity.WARNING,
            message=(
                f"Title is {len(title)} characters; search results cut it after "
                f"about {limit}. Set a shorter SEO title on the Promote tab."
            ),
        )
    ]


@register_check
def check_meta_description(inspected: InspectedPage) -> list[FindingData]:
    meta = inspected.html.find("meta", attrs={"name": "description"})
    description = _attribute(meta, "content").strip() if isinstance(meta, Tag) else ""
    limit = settings.SEO_DESCRIPTION_MAX_LENGTH
    if not description:
        return [
            FindingData(
                code=MISSING_DESCRIPTION,
                severity=Finding.Severity.WARNING,
                message="Page has no meta description for search results.",
            )
        ]
    if len(description) > limit:
        return [
            FindingData(
                code=LONG_DESCRIPTION,
                severity=Finding.Severity.WARNING,
                message=(
                    f"Meta description is {len(description)} characters; "
                    f"keep it to {limit}."
                ),
            )
        ]
    return []


@register_check
def check_canonical(inspected: InspectedPage) -> list[FindingData]:
    canonical = inspected.html.find("link", rel="canonical")
    if isinstance(canonical, Tag) and _attribute(canonical, "href").strip():
        return []
    return [
        FindingData(
            code=MISSING_CANONICAL,
            severity=Finding.Severity.WARNING,
            message="Page has no canonical link, so duplicate URLs can compete.",
        )
    ]


@register_check
def check_hreflang(inspected: InspectedPage) -> list[FindingData]:
    expected = set(inspected.translations)
    if len(expected) < 2:
        return []
    declared = {
        _attribute(link, "hreflang")
        for link in inspected.html.find_all("link", rel="alternate")
        if link.has_attr("hreflang")
    }
    missing = sorted((expected | {X_DEFAULT}) - declared)
    return [
        FindingData(
            code=MISSING_HREFLANG,
            severity=Finding.Severity.WARNING,
            message=f"No hreflang alternate for “{code}”, though the page has one.",
            fingerprint=code,
            language_code=code if code != X_DEFAULT else None,
        )
        for code in missing
    ]


@register_check
def check_h1_count(inspected: InspectedPage) -> list[FindingData]:
    count = len(inspected.html.find_all("h1"))
    if count == 1:
        return []
    return [
        FindingData(
            code=H1_COUNT,
            severity=Finding.Severity.ERROR,
            message=f"Page has {count} main headings (h1); it should have exactly one.",
        )
    ]


def _attribute(element: Tag, name: str) -> str:
    value = element.get(name, "")
    return " ".join(value) if isinstance(value, list) else str(value)
