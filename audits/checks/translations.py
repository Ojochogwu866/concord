from datetime import datetime

from django.conf import settings
from django.utils.translation import get_language_info

from audits.models import Finding
from audits.registry import FindingData, InspectedPage, register_check

MISSING_TRANSLATION = "i18n.missing_translation"
STALE_TRANSLATION = "i18n.stale_translation"


@register_check
def check_translations(inspected: InspectedPage) -> list[FindingData]:
    page = inspected.page
    source_language = page.locale.language_code
    if source_language != settings.LANGUAGE_CODE:
        return []

    findings = []
    for language_code, _ in settings.WAGTAIL_CONTENT_LANGUAGES:
        if language_code == source_language:
            continue
        language_name = get_language_info(language_code)["name"]
        translation = inspected.translations.get(language_code)
        if translation is None:
            findings.append(
                FindingData(
                    code=MISSING_TRANSLATION,
                    severity=Finding.Severity.ERROR,
                    message=f"No {language_name} version of this page is published.",
                    language_code=language_code,
                )
            )
        elif _is_older(translation.last_published_at, page.last_published_at):
            findings.append(
                FindingData(
                    code=STALE_TRANSLATION,
                    severity=Finding.Severity.WARNING,
                    message=(
                        f"The {language_name} version was last published before "
                        "the page it was translated from."
                    ),
                    language_code=language_code,
                )
            )
    return findings


def _is_older(translated_at: datetime | None, source_at: datetime | None) -> bool:
    if translated_at is None or source_at is None:
        return False
    return translated_at < source_at
