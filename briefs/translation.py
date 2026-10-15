from wagtail.models import DraftStateMixin, Locale, TranslatableMixin
from wagtail_localize.models import Translation, TranslationSource


class MissingTranslationError(Exception):
    pass


def ensure_translation(
    instance: TranslatableMixin, locale: Locale, strings: dict[str, str]
) -> None:
    if instance.has_translation(locale):
        return
    source, _ = TranslationSource.get_or_create_from_instance(instance)
    translation, _ = Translation.objects.get_or_create(
        source=source, target_locale=locale
    )
    po_file = translation.export_po()
    for entry in po_file:
        if entry.msgid not in strings:
            raise MissingTranslationError(
                f"No {locale.language_code} translation for {entry.msgid!r} "
                f"({entry.msgctxt}) on {instance}."
            )
        entry.msgstr = strings[entry.msgid]
    translation.import_po(po_file)

    if isinstance(instance, DraftStateMixin):
        # wagtail-localize defers publishing to commit, when the queued revision is
        # stale and would reset the parent's child count, so save a draft and publish.
        translation.save_target(publish=False)
        translation.get_target_instance().get_latest_revision().publish()
    else:
        translation.save_target()
