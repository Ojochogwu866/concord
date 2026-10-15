import importlib
import json

import pytest
from django.apps import apps

from briefs.models import BriefPage
from briefs.reading_time import (
    WORDS_PER_MINUTE,
    estimate_reading_minutes,
    stream_text,
)
from briefs.tests.fixtures import BriefFactory

backfill_migration = importlib.import_module(
    "briefs.migrations.0005_backfill_reading_time"
)


@pytest.mark.parametrize(
    ("word_count", "minutes"),
    [(0, 1), (1, 1), (WORDS_PER_MINUTE, 1), (WORDS_PER_MINUTE + 1, 2)],
)
def test_rounds_up_to_whole_minutes(word_count: int, minutes: int) -> None:
    assert estimate_reading_minutes("word " * word_count) == minutes


def test_stream_text_reads_text_and_skips_structure() -> None:
    raw = [
        {"type": "heading", "value": {"text": "What changed", "level": "h2"}},
        {"type": "paragraph", "value": "<p>Prices <b>fell</b>.</p>"},
        {"type": "figure", "value": {"image": {"image": 7, "alt_text": "Alt"}}},
    ]

    assert stream_text(raw).split() == ["What", "changed", "Prices", "fell."]


def long_body(word_count: int) -> str:
    paragraph = "<p>" + "word " * word_count + "</p>"
    return json.dumps([{"type": "paragraph", "value": paragraph}])


def test_saving_a_brief_sets_its_reading_time(make_brief: BriefFactory) -> None:
    brief = make_brief(body=long_body(WORDS_PER_MINUTE * 3))

    assert BriefPage.objects.get(pk=brief.pk).reading_time == 4


def test_republishing_recalculates_reading_time(make_brief: BriefFactory) -> None:
    brief = make_brief()
    brief.body = long_body(WORDS_PER_MINUTE * 5)
    brief.save_revision().publish()

    assert BriefPage.objects.get(pk=brief.pk).reading_time == 6


def test_backfill_fills_missing_values_and_is_idempotent(
    make_brief: BriefFactory,
) -> None:
    brief = make_brief(body=long_body(WORDS_PER_MINUTE * 2))
    BriefPage.objects.filter(pk=brief.pk).update(reading_time=None)

    backfill_migration.backfill_reading_time(apps, schema_editor=None)
    backfill_migration.backfill_reading_time(apps, schema_editor=None)

    assert BriefPage.objects.get(pk=brief.pk).reading_time == 3
