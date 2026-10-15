from http import HTTPStatus

from django.conf import settings
from django.test import Client

FALLBACK_HOST = "localhost"


class PageRenderError(Exception):
    pass


def render_page_html(path: str) -> str:
    # Rendering through the full middleware stack makes the audit see exactly what
    # visitors get, including the language prefix and security redirects.
    client = Client(raise_request_exception=False)
    response = client.get(path, secure=True, headers={"host": _request_host()})
    if response.status_code != HTTPStatus.OK:
        raise PageRenderError(f"Rendering {path} returned HTTP {response.status_code}.")
    charset = response.charset or "utf-8"
    return response.content.decode(charset)


def _request_host() -> str:
    for host in settings.ALLOWED_HOSTS:
        if host != "*":
            return host.lstrip(".")
    return FALLBACK_HOST
