import pytest

from briefs.templatetags.briefs_tags import split_last_word


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
