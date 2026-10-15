import math
from collections.abc import Mapping, Sequence

from django.db import migrations
from django.utils.html import strip_tags

# Frozen copy of briefs.reading_time, so this migration never changes behaviour.
WORDS_PER_MINUTE = 200
NON_TEXT_KEYS = {"type", "id", "level", "image", "decorative", "alt_text"}
BATCH_SIZE = 500


def text_parts(value):
    if isinstance(value, str):
        yield strip_tags(value)
    elif isinstance(value, Mapping):
        for key, item in value.items():
            if key not in NON_TEXT_KEYS:
                yield from text_parts(item)
    elif isinstance(value, Sequence):
        for item in value:
            yield from text_parts(item)


def backfill_reading_time(apps, schema_editor):
    BriefPage = apps.get_model("briefs", "BriefPage")
    briefs = []
    for brief in BriefPage.objects.only("summary", "body").iterator(chunk_size=BATCH_SIZE):
        text = " ".join([brief.summary, *text_parts(brief.body.raw_data)])
        brief.reading_time = max(1, math.ceil(len(text.split()) / WORDS_PER_MINUTE))
        briefs.append(brief)
    BriefPage.objects.bulk_update(briefs, ["reading_time"], batch_size=BATCH_SIZE)


class Migration(migrations.Migration):

    dependencies = [
        ("briefs", "0004_brief_reading_time"),
    ]

    operations = [
        migrations.RunPython(backfill_reading_time, reverse_code=migrations.RunPython.noop),
    ]
