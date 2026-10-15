import pytest
from django.core.exceptions import ImproperlyConfigured

from sitehealth.settings.environment import (
    get_list,
    get_required,
    get_required_list,
    r2_storage,
)


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


R2_ENVIRONMENT = {
    "R2_BUCKET_NAME": "concord-media",
    "R2_BUCKET_URL": "https://account.r2.cloudflarestorage.com/concord-media",
    "R2_ACCESS_KEY_ID": "test-access-key",
    "R2_SECRET_ACCESS_KEY": "test-secret-key",
}


def set_r2_environment(monkeypatch: pytest.MonkeyPatch, **overrides: str) -> None:
    for name, value in {**R2_ENVIRONMENT, **overrides}.items():
        monkeypatch.setenv(name, value)


def test_r2_storage_is_off_without_a_bucket(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("R2_BUCKET_NAME", raising=False)

    assert r2_storage() is None


def test_r2_storage_uses_signed_urls_for_a_private_bucket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    set_r2_environment(monkeypatch)
    monkeypatch.delenv("R2_PUBLIC_URL", raising=False)

    storage = r2_storage()

    assert storage is not None
    options = storage["OPTIONS"]
    assert isinstance(options, dict)
    assert options["endpoint_url"] == "https://account.r2.cloudflarestorage.com"
    assert options["bucket_name"] == "concord-media"
    assert options["querystring_auth"] is True
    assert options["custom_domain"] is None


def test_r2_storage_serves_public_domain_without_signing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    set_r2_environment(monkeypatch, R2_PUBLIC_URL="https://media.example.com")

    storage = r2_storage()

    assert storage is not None
    options = storage["OPTIONS"]
    assert isinstance(options, dict)
    assert options["custom_domain"] == "media.example.com"
    assert options["querystring_auth"] is False


def test_r2_storage_requires_every_credential(monkeypatch: pytest.MonkeyPatch) -> None:
    set_r2_environment(monkeypatch)
    monkeypatch.delenv("R2_SECRET_ACCESS_KEY")

    with pytest.raises(ImproperlyConfigured, match="R2_SECRET_ACCESS_KEY"):
        r2_storage()


def test_r2_storage_rejects_insecure_bucket_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    set_r2_environment(monkeypatch, R2_BUCKET_URL="http://account.example.com/bucket")

    with pytest.raises(ImproperlyConfigured, match="https"):
        r2_storage()
