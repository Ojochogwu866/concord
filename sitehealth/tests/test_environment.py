import pytest
from django.core.exceptions import ImproperlyConfigured

from sitehealth.settings.environment import get_list, get_required, get_required_list


def test_get_required_returns_stripped_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SITEHEALTH_SAMPLE", "  value  ")

    assert get_required("SITEHEALTH_SAMPLE") == "value"


@pytest.mark.parametrize("raw", [None, "", "   "])
def test_get_required_rejects_missing_or_blank(
    monkeypatch: pytest.MonkeyPatch, raw: str | None
) -> None:
    if raw is None:
        monkeypatch.delenv("SITEHEALTH_SAMPLE", raising=False)
    else:
        monkeypatch.setenv("SITEHEALTH_SAMPLE", raw)

    with pytest.raises(ImproperlyConfigured, match="SITEHEALTH_SAMPLE"):
        get_required("SITEHEALTH_SAMPLE")


def test_get_list_splits_and_drops_empty_items(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SITEHEALTH_SAMPLE", "a.example.com, ,b.example.com,")

    assert get_list("SITEHEALTH_SAMPLE") == ["a.example.com", "b.example.com"]


def test_get_list_uses_default_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SITEHEALTH_SAMPLE", raising=False)

    assert get_list("SITEHEALTH_SAMPLE", default="localhost") == ["localhost"]


def test_get_required_list_rejects_empty_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SITEHEALTH_SAMPLE", " , ")

    with pytest.raises(ImproperlyConfigured, match="SITEHEALTH_SAMPLE"):
        get_required_list("SITEHEALTH_SAMPLE")
