import logging

from django.contrib.auth.models import User

from suggestions.models import ProviderCall
from suggestions.prompts import build_prompt
from suggestions.providers import (
    ProviderError,
    ProviderResponse,
    SuggestionProvider,
    SuggestionRequest,
    configured_provider_path,
)

logger = logging.getLogger(__name__)
ERROR_MAX_LENGTH = 255


def call_provider(
    provider: SuggestionProvider,
    request: SuggestionRequest,
    user: User | None = None,
) -> tuple[ProviderCall, ProviderResponse]:
    prompt = build_prompt(request)
    call = ProviderCall(
        task=request.task,
        provider=configured_provider_path(),
        prompt=prompt,
        requested_by=user,
    )
    try:
        response = provider.suggest(request, prompt)
    except ProviderError as error:
        call.error = str(error)[:ERROR_MAX_LENGTH]
        call.save()
        logger.warning(
            "Provider call %s for %s failed: %s", call.pk, request.task, error
        )
        raise
    call.response = response.text
    call.model_name = response.model_name
    call.save()
    return call, response
