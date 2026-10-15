from pytest_django.fixtures import Settings
from wagtail.models import Locale
from wagtail_localize.strings import StringValue

from briefs.site_setup import SiteStructure
from suggestions.models import ProviderCall
from suggestions.translator import ConcordTranslator


def locales() -> tuple[Locale, Locale]:
    return Locale.objects.get(language_code="en"), Locale.objects.get(
        language_code="fr"
    )


def test_drafts_each_string_and_keeps_link_placeholders(
    site_structure: SiteStructure,
) -> None:
    english, french = locales()
    source = StringValue('Read the <a id="a1">full study</a>.')

    translations = ConcordTranslator({}).translate(english, french, [source])

    assert '<a id="a1">full study</a>' in translations[source].data
    call = ProviderCall.objects.get()
    assert "from English to French" in call.prompt
    assert "<a id=...> placeholder" in call.prompt


def test_offers_translation_only_between_different_languages(
    site_structure: SiteStructure,
) -> None:
    english, french = locales()
    translator = ConcordTranslator({})

    assert translator.can_translate(english, french)
    assert not translator.can_translate(english, english)


def test_is_unavailable_without_a_provider(
    site_structure: SiteStructure, settings: Settings
) -> None:
    settings.SUGGESTIONS_PROVIDER = ""
    english, french = locales()

    assert not ConcordTranslator({}).can_translate(english, french)
