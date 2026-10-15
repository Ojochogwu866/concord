import pytest
from django.db import OperationalError
from django.test import Client


@pytest.mark.django_db
def test_reports_ok_without_a_language_redirect(client: Client) -> None:
    response = client.get("/healthz/")

    assert response.status_code == 200
    assert response.content == b"ok"


@pytest.mark.django_db
def test_reports_unavailable_when_the_database_is_down(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse_connection() -> None:
        raise OperationalError("connection refused")

    monkeypatch.setattr(
        "sitehealth.views.connection.ensure_connection", refuse_connection
    )

    response = client.get("/healthz/")

    assert response.status_code == 503
