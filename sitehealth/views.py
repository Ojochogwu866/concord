import logging
from http import HTTPStatus

from django.db import OperationalError, connection
from django.http import HttpRequest, HttpResponse

logger = logging.getLogger(__name__)


def healthz(request: HttpRequest) -> HttpResponse:
    try:
        connection.ensure_connection()
    except OperationalError:
        logger.exception("Health check could not reach the database.")
        return HttpResponse(
            "database unavailable",
            status=HTTPStatus.SERVICE_UNAVAILABLE,
            content_type="text/plain",
        )
    return HttpResponse("ok", content_type="text/plain")
