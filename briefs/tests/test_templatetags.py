import pytest
from django.conf import settings

from briefs.models import BriefPage
from briefs.templatetags.briefs_tags import meta_description, split_last_word


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("This site checks its own work.", ("This site checks its own", "work.")),
        ("  Briefs  ", ("", "Briefs")),
        ("", ("", "")),
    ],
)
def test_split_last_word(text: str, expected: tuple[str, str]) -> None:
    assert split_last_word(text) == expected


def test_meta_description_prefers_the_editor_description() -> None:
    page = BriefPage(search_description="Written for search.", summary="Summary.")

    assert meta_description(page) == "Written for search."


def test_meta_description_shortens_long_fallbacks_at_a_word() -> None:
    page = BriefPage(summary="word " * 100)

    description = meta_description(page)

    assert len(description) <= settings.SEO_DESCRIPTION_MAX_LENGTH
    assert description.endswith("word…")


def test_meta_description_ignores_values_that_are_not_pages() -> None:
    assert meta_description("") == ""
