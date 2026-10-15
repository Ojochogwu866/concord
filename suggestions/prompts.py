from django.utils.translation import get_language_info

from suggestions.models import Task
from suggestions.providers import SuggestionRequest


def build_prompt(request: SuggestionRequest) -> str:
    language = _language_name(request.language_code)
    if request.task == Task.TRANSLATION:
        target = _language_name(request.target_language_code)
        return (
            f"Translate the text below from {language} to {target} for a public "
            "website. Keep every HTML tag and every <a id=...> placeholder exactly "
            "as it is. Reply with the translation only.\n\n"
            f"{request.source_text}"
        )
    if request.task == Task.SEO_TITLE:
        return (
            f"Write a title for search results, in {language}, of at most "
            f"{request.max_length} characters. Keep the page's meaning and key "
            "terms. Reply with the title only, without quotation marks.\n\n"
            f"Current title: {request.source_text}\n"
            f"Summary: {request.context}"
        )
    return (
        f"Write a meta description for search results, in {language}, of at most "
        f"{request.max_length} characters. Describe what the reader will learn. "
        "Reply with the description only, without quotation marks.\n\n"
        f"Page title: {request.context}\n"
        f"Page text: {request.source_text}"
    )


def _language_name(language_code: str) -> str:
    name: str = get_language_info(language_code)["name"]
    return name
