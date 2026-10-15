import re

import pytest
from django.template.loader import render_to_string
from django.test import Client


@pytest.mark.django_db
def test_missing_page_renders_not_found_template(client: Client) -> None:
    response = client.get("/this-page-does-not-exist/")

    html = response.content.decode()
    assert response.status_code == 404
    assert '<html lang="en">' in html
    assert 'href="#main"' in html
    assert len(re.findall(r"<h1\b", html)) == 1
    assert "Page not found" in html


def test_server_error_template_renders_without_request_context() -> None:
    html = render_to_string("500.html")

    assert '<html lang="en">' in html
    assert len(re.findall(r"<h1\b", html)) == 1
    assert "Something went wrong" in html
