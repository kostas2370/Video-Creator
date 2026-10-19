"""Safe API failures with matching server-side error references."""

import logging

from rest_framework.response import Response
from rest_framework.views import exception_handler, set_rollback

from .observability import current_request_id

logger = logging.getLogger(__name__)


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None and response.status_code < 500:
        return response

    logger.error(
        "api_request_failed",
        exc_info=(type(exc), exc, exc.__traceback__),
        extra={"status_code": response.status_code if response is not None else 500},
    )
    if response is None:
        set_rollback()
        response = Response(
            {"detail": "Something went wrong. Please try again."}, status=500
        )
    if isinstance(response.data, dict):
        response.data["request_id"] = current_request_id()
    return response
