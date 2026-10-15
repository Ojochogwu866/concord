import math
from collections.abc import Iterator, Mapping, Sequence

from django.utils.html import strip_tags

WORDS_PER_MINUTE = 200
NON_TEXT_KEYS = {"type", "id", "level", "image", "decorative", "alt_text"}


def estimate_reading_minutes(text: str) -> int:
    return max(1, math.ceil(len(text.split()) / WORDS_PER_MINUTE))


def stream_text(raw_data: object) -> str:
    return " ".join(_text_parts(raw_data))


def _text_parts(value: object) -> Iterator[str]:
    if isinstance(value, str):
        yield strip_tags(value)
    elif isinstance(value, Mapping):
        for key, item in value.items():
            if key not in NON_TEXT_KEYS:
                yield from _text_parts(item)
    elif isinstance(value, Sequence):
        for item in value:
            yield from _text_parts(item)
