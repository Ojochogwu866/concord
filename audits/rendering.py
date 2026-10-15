from http import HTTPStatus

from django.conf import settings
from django.http import HttpResponse, HttpResponseBase
from django.test import Client

FALLBACK_HOST = "localhost"
MAX_REDIRECTS = 5
REDIRECT_STATUSES = {
    HTTPStatus.MOVED_PERMANENTLY,
    HTTPStatus.FOUND,
    HTTPStatus.SEE_OTHER,
    HTTPStatus.TEMPORARY_REDIRECT,
    HTTPStatus.PERMANENT_REDIRECT,
}


class PageRenderError(Exception):
    pass


def render_page_html(path: str) -> str:
    response = _request(path)
    if response.status_code != HTTPStatus.OK:
        raise PageRenderError(f"Rendering {path} returned HTTP {response.status_code}.")
    if not isinstance(response, HttpResponse):
        raise PageRenderError(f"Rendering {path} returned a streamed response.")
    return response.content.decode(response.charset or "utf-8")


def fetch_final_status(path: str) -> int:
    for _ in range(MAX_REDIRECTS + 1):
        response = _request(path)
        location = response.get("Location", "")
        if response.status_code not in REDIRECT_STATUSES or not location.startswith(
            "/"
        ):
            status: int = response.status_code
            return status
        path = location
    return HTTPStatus.LOOP_DETECTED


def _request(path: str) -> HttpResponseBase:
    # Requests go through the full middleware stack so the audit sees exactly what
    # visitors get, including language prefixes, redirects and security settings.
    client = Client(raise_request_exception=False)
    response: HttpResponseBase = client.get(
        path, secure=True, headers={"host": _request_host()}
    )
    return response


def _request_host() -> str:
    for host in settings.ALLOWED_HOSTS:
        if host != "*":
            return host.lstrip(".")
    return FALLBACK_HOST
