from suggestions.models import Task
from suggestions.providers import ProviderResponse, SuggestionRequest

MODEL_NAME = "offline-placeholder"
PLACEHOLDER_PREFIX = "[draft]"


class OfflineProvider:
    """Deterministic placeholder text for development and tests; never a real draft."""

    def suggest(self, request: SuggestionRequest, prompt: str) -> ProviderResponse:
        if request.task == Task.TRANSLATION:
            text = f"{PLACEHOLDER_PREFIX} {request.source_text}"
        else:
            text = _fit(
                f"{PLACEHOLDER_PREFIX} {request.source_text}", request.max_length
            )
        return ProviderResponse(text=text, model_name=MODEL_NAME)


def _fit(text: str, max_length: int | None) -> str:
    if max_length is None or len(text) <= max_length:
        return text
    return text[:max_length].rsplit(" ", 1)[0]
