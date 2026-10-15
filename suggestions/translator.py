import logging

from django.utils.translation import gettext_lazy as _
from wagtail.models import Locale
from wagtail_localize.machine_translators.base import BaseMachineTranslator
from wagtail_localize.strings import StringValue

from suggestions.calls import call_provider
from suggestions.models import Task
from suggestions.providers import ProviderError, SuggestionRequest, get_provider

logger = logging.getLogger(__name__)


class ConcordTranslator(BaseMachineTranslator):
    display_name = _("Concord draft translator")

    def can_translate(self, source_locale: Locale, target_locale: Locale) -> bool:
        return get_provider() is not None and _language(source_locale) != _language(
            target_locale
        )

    def translate(
        self, source_locale: Locale, target_locale: Locale, strings: list[StringValue]
    ) -> dict[StringValue, StringValue]:
        provider = get_provider()
        if provider is None:
            return {}
        translations = {}
        for string in strings:
            request = SuggestionRequest(
                task=Task.TRANSLATION,
                source_text=string.data,
                language_code=source_locale.language_code,
                target_language_code=target_locale.language_code,
            )
            try:
                _, response = call_provider(provider, request)
            except ProviderError:
                logger.warning("Skipped one string while drafting a translation.")
                continue
            translations[string] = StringValue(response.text)
        return translations


def _language(locale: Locale) -> str:
    code: str = locale.language_code
    return code.split("-")[0]
