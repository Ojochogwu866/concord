import pytest
from django.utils import timezone
from pytest_django.fixtures import Settings

from audits.models import AuditRun, Finding
from briefs.models import BriefPage
from briefs.tests.fixtures import BriefFactory
from suggestions.generation import (
    InvalidSuggestionError,
    SuggestionsDisabledError,
    clean_suggestion,
    findings_needing_suggestions,
    suggest_fixes,
)
from suggestions.models import ProviderCall, Suggestion, Task
from suggestions.prompts import build_prompt
from suggestions.providers import ProviderError, ProviderResponse, SuggestionRequest

LONG_TITLE = "A title that is far too long to show in full in any search result page"


class FailingProvider:
    def suggest(self, request: SuggestionRequest, prompt: str) -> ProviderResponse:
        raise ProviderError("model unavailable")


class RamblingProvider:
    def suggest(self, request: SuggestionRequest, prompt: str) -> ProviderResponse:
        return ProviderResponse(text="word " * 100, model_name="rambler")


def add_finding(brief: BriefPage, code: str) -> Finding:
    run = AuditRun.objects.create(
        status=AuditRun.Status.SUCCEEDED, finished_at=timezone.now()
    )
    return Finding.objects.create(
        run=run,
        page=brief,
        locale=brief.locale,
        code=code,
        severity=Finding.Severity.WARNING,
        message="Example.",
    )


def test_drafts_a_title_within_the_limit(make_brief: BriefFactory) -> None:
    finding = add_finding(make_brief(title=LONG_TITLE), "seo.long_title")

    report = suggest_fixes(limit=5)

    suggestion = Suggestion.objects.get(finding=finding)
    assert (report.created, report.failed) == (1, 0)
    assert suggestion.task == Task.SEO_TITLE
    assert suggestion.status == Suggestion.Status.PENDING
    assert len(suggestion.proposed_text) <= 60
    assert "at most 60 characters" in suggestion.call.prompt


def test_drafts_a_description_from_the_summary(make_brief: BriefFactory) -> None:
    brief = make_brief(summary="Battery storage now clears the evening peak.")
    add_finding(brief, "seo.missing_description")

    suggest_fixes(limit=5)

    suggestion = Suggestion.objects.get()
    assert suggestion.task == Task.META_DESCRIPTION
    assert "Battery storage now clears the evening peak." in suggestion.proposed_text


def test_skips_unsupported_codes_and_pending_findings(make_brief: BriefFactory) -> None:
    brief = make_brief(title=LONG_TITLE)
    add_finding(brief, "i18n.missing_translation")
    add_finding(brief, "seo.long_title")
    suggest_fixes(limit=5)

    second = suggest_fixes(limit=5)

    assert second.created == 0
    assert Suggestion.objects.count() == 1


def test_respects_the_per_run_limit(make_brief: BriefFactory) -> None:
    for number in range(3):
        add_finding(make_brief(title=f"{LONG_TITLE} {number}"), "seo.long_title")

    assert suggest_fixes(limit=2).created == 2
    assert findings_needing_suggestions().count() == 1


def test_provider_failure_is_logged_without_a_suggestion(
    make_brief: BriefFactory, settings: Settings
) -> None:
    settings.SUGGESTIONS_PROVIDER = f"{__name__}.FailingProvider"
    add_finding(make_brief(title=LONG_TITLE), "seo.long_title")

    report = suggest_fixes(limit=5)

    assert (report.created, report.failed) == (0, 1)
    assert not Suggestion.objects.exists()
    assert ProviderCall.objects.get().error == "model unavailable"


def test_overlong_answers_are_rejected(
    make_brief: BriefFactory, settings: Settings
) -> None:
    settings.SUGGESTIONS_PROVIDER = f"{__name__}.RamblingProvider"
    add_finding(make_brief(title=LONG_TITLE), "seo.long_title")

    assert suggest_fixes(limit=5).failed == 1
    assert not Suggestion.objects.exists()


def test_suggestions_are_off_without_a_provider(settings: Settings) -> None:
    settings.SUGGESTIONS_PROVIDER = ""

    with pytest.raises(SuggestionsDisabledError):
        suggest_fixes(limit=5)


@pytest.mark.parametrize(
    ("raw", "cleaned"),
    [('  "A short title"  ', "A short title"), ("«Titre court»", "Titre court")],
)
def test_cleans_quotes_and_whitespace(raw: str, cleaned: str) -> None:
    assert clean_suggestion(raw, 60) == cleaned


@pytest.mark.parametrize("raw", ["", "   ", '""'])
def test_rejects_empty_answers(raw: str) -> None:
    with pytest.raises(InvalidSuggestionError):
        clean_suggestion(raw, 60)


def test_prompts_name_the_language_and_limit() -> None:
    prompt = build_prompt(
        SuggestionRequest(
            task=Task.META_DESCRIPTION,
            source_text="Texte",
            language_code="fr",
            context="Titre",
            max_length=160,
        )
    )

    assert "in French" in prompt
    assert "at most 160 characters" in prompt
