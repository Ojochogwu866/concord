from dataclasses import dataclass
from typing import Protocol

from django.conf import settings
from django.utils.module_loading import import_string

from suggestions.models import Task


class ProviderError(Exception):
    pass


@dataclass(frozen=True)
class SuggestionRequest:
    task: Task
    source_text: str
    language_code: str
    target_language_code: str = ""
    context: str = ""
    max_length: int | None = None


@dataclass(frozen=True)
class ProviderResponse:
    text: str
    model_name: str


class SuggestionProvider(Protocol):
    def suggest(self, request: SuggestionRequest, prompt: str) -> ProviderResponse: ...


def configured_provider_path() -> str:
    path: str = settings.SUGGESTIONS_PROVIDER
    return path


def get_provider() -> SuggestionProvider | None:
    path = configured_provider_path()
    if not path:
        return None
    provider: SuggestionProvider = import_string(path)()
    return provider
