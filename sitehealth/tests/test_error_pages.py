import re

import pytest
from django.template.loader import render_to_string
from django.test import Client
from django.utils import translation


@pytest.mark.django_db
def test_unprefixed_path_redirects_to_default_language(client: Client) -> None:
    response = client.get("/this-page-does-not-exist/")

    assert response.status_code == 302
    assert response["Location"] == "/en/this-page-does-not-exist/"


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("language", "heading"),
    [("en", "Page not found"), ("fr", "Page introuvable")],
)
def test_missing_page_renders_not_found_template_in_each_language(
    client: Client, language: str, heading: str
) -> None:
    response = client.get(f"/{language}/this-page-does-not-exist/")

    html = response.content.decode()
    assert response.status_code == 404
    assert f'<html lang="{language}">' in html
    assert 'href="#main"' in html
    assert len(re.findall(r"<h1\b", html)) == 1
    assert heading in html


@pytest.mark.parametrize(
    ("language", "heading"),
    [("en", "Something went"), ("fr", "Quelque chose s’est")],
)
def test_server_error_template_renders_without_request_context(
    language: str, heading: str
) -> None:
    with translation.override(language):
        html = render_to_string("500.html")

    assert f'<html lang="{language}">' in html
    assert len(re.findall(r"<h1\b", html)) == 1
    assert heading in html
