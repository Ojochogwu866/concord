import logging
from dataclasses import dataclass

from django.conf import settings
from django.db.models import QuerySet
from django.utils.html import strip_tags

from audits.models import Finding
from briefs.reading_time import stream_text
from suggestions.calls import call_provider
from suggestions.models import Suggestion, Task
from suggestions.providers import (
    ProviderError,
    SuggestionProvider,
    SuggestionRequest,
    get_provider,
)

logger = logging.getLogger(__name__)

TASK_FOR_CODE = {
    "seo.long_title": Task.SEO_TITLE,
    "seo.missing_description": Task.META_DESCRIPTION,
}
QUOTE_CHARACTERS = "\"'“”«»"
DESCRIPTION_SOURCE_FIELDS = ("summary", "lead", "intro")


class SuggestionsDisabledError(Exception):
    pass


class InvalidSuggestionError(Exception):
    pass


@dataclass(frozen=True)
class GenerationReport:
    created: int
    failed: int


def suggest_fixes(limit: int) -> GenerationReport:
    provider = get_provider()
    if provider is None:
        raise SuggestionsDisabledError(
            "Set SUGGESTIONS_PROVIDER to turn suggestions on."
        )
    created = failed = 0
    for finding in findings_needing_suggestions()[:limit]:
        try:
            create_suggestion(finding, provider)
            created += 1
        except (ProviderError, InvalidSuggestionError) as error:
            logger.warning("No suggestion for finding %s: %s", finding.pk, error)
            failed += 1
    return GenerationReport(created=created, failed=failed)


def findings_needing_suggestions() -> QuerySet[Finding]:
    return (
        Finding.objects.filter(
            resolved_at__isnull=True,
            code__in=TASK_FOR_CODE,
            page__isnull=False,
        )
        .exclude(suggestions__status=Suggestion.Status.PENDING)
        .select_related("page", "locale")
        .order_by("first_seen_at")
    )


def create_suggestion(finding: Finding, provider: SuggestionProvider) -> Suggestion:
    task = TASK_FOR_CODE[finding.code]
    request = build_request(finding, task)
    call, response = call_provider(provider, request)
    text = clean_suggestion(response.text, request.max_length)
    return Suggestion.objects.create(
        finding=finding, task=task, proposed_text=text, call=call
    )


def build_request(finding: Finding, task: Task) -> SuggestionRequest:
    if finding.page is None:
        raise InvalidSuggestionError("The finding's page no longer exists.")
    page = finding.page.specific
    language_code = page.locale.language_code
    if task == Task.SEO_TITLE:
        return SuggestionRequest(
            task=task,
            source_text=page.title,
            language_code=language_code,
            context=_description_source(page),
            max_length=settings.SEO_TITLE_MAX_LENGTH,
        )
    return SuggestionRequest(
        task=task,
        source_text=_description_source(page),
        language_code=language_code,
        context=page.title,
        max_length=settings.SEO_DESCRIPTION_MAX_LENGTH,
    )


def clean_suggestion(text: str, max_length: int | None) -> str:
    cleaned = " ".join(text.split()).strip(QUOTE_CHARACTERS).strip()
    if not cleaned:
        raise InvalidSuggestionError("The model returned no text.")
    if max_length is not None and len(cleaned) > max_length:
        raise InvalidSuggestionError(
            f"The model returned {len(cleaned)} characters; the limit is {max_length}."
        )
    return cleaned


def _description_source(page: object) -> str:
    for field in DESCRIPTION_SOURCE_FIELDS:
        value = getattr(page, field, "")
        if value:
            return " ".join(strip_tags(str(value)).split())
    body = getattr(page, "body", None)
    return stream_text(body.raw_data) if body is not None else ""
