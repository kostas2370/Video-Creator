"""Request references and structured console logs for the API and workers."""

import json
import logging
from contextvars import ContextVar
from datetime import datetime, timezone
from time import monotonic
from uuid import uuid4

from asgiref.sync import iscoroutinefunction
from celery import current_task
from django.utils.decorators import sync_and_async_middleware

request_context = ContextVar("request_context", default=None)
logger = logging.getLogger(__name__)


def current_request_id():
    request = request_context.get()
    if request is not None:
        return request.request_id
    if current_task:
        return (current_task.request.headers or {}).get("request_id")
    return None


class JsonFormatter(logging.Formatter):
    def format(self, record):
        entry = {
            "timestamp": datetime.fromtimestamp(
                record.created, timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        reference = current_request_id()
        if reference:
            entry["request_id"] = reference
        request = request_context.get() or getattr(record, "request", None)
        if request is not None:
            entry["method"] = request.method
            match = getattr(request, "resolver_match", None)
            if match:
                entry["view"] = match.view_name
        if current_task and current_task.request.id:
            entry.update(task_id=current_task.request.id, task_name=current_task.name)
        for field in ("status_code", "duration_ms", "video_id", "scene_id"):
            if hasattr(record, field):
                entry[field] = getattr(record, field)
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str, ensure_ascii=False)


def propagate_request_id(sender=None, headers=None, **kwargs):
    reference = current_request_id()
    if headers is not None and reference:
        headers["request_id"] = reference


@sync_and_async_middleware
def request_logging(get_response):
    def start(request):
        # Generate our own reference; never trust a caller-supplied logging ID.
        request.request_id = uuid4().hex
        return request_context.set(request), monotonic()

    def finish(request, response, started):
        response["X-Request-ID"] = request.request_id
        if request.path.startswith("/api/"):
            logger.info(
                "request_finished",
                extra={
                    "status_code": response.status_code,
                    "duration_ms": round((monotonic() - started) * 1000, 1),
                },
            )
        return response

    if iscoroutinefunction(get_response):

        async def middleware(request):
            token, started = start(request)
            try:
                return finish(request, await get_response(request), started)
            finally:
                request_context.reset(token)
    else:

        def middleware(request):
            token, started = start(request)
            try:
                return finish(request, get_response(request), started)
            finally:
                request_context.reset(token)

    return middleware


def api_exception_handler(exc, context):
    from rest_framework.response import Response
    from rest_framework.views import exception_handler, set_rollback

    response = exception_handler(exc, context)
    if response is None or response.status_code >= 500:
        code = response.status_code if response is not None else 500
        logger.error(
            "api_request_failed",
            exc_info=(type(exc), exc, exc.__traceback__),
            extra={"status_code": code},
        )
        if response is None:
            set_rollback()
            response = Response(
                {"detail": "Something went wrong. Please try again."}, status=500
            )
        if isinstance(response.data, dict):
            response.data["request_id"] = current_request_id()
    return response
