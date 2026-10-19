"""Request references and structured console logs for the API and workers."""

import json
import logging
from contextvars import ContextVar
from datetime import datetime, timezone
from uuid import uuid4

from asgiref.sync import iscoroutinefunction
from celery import current_task
from django.utils.decorators import sync_and_async_middleware

request_context = ContextVar("request_context", default=None)


def current_request_id(request=None):
    reference = getattr(request_context.get() or request, "request_id", None)
    if reference:
        return reference
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
        request = request_context.get() or getattr(record, "request", None)
        reference = current_request_id(request)
        if reference:
            entry["request_id"] = reference
        if request is not None:
            entry["method"] = request.method
            match = getattr(request, "resolver_match", None)
            if match:
                entry["view"] = match.view_name
        if current_task and current_task.request.id:
            entry.update(task_id=current_task.request.id, task_name=current_task.name)
        for field in ("status_code", "video_id", "scene_id"):
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
        request.request_id = uuid4().hex
        return request_context.set(request)

    if iscoroutinefunction(get_response):

        async def middleware(request):
            token = start(request)
            try:
                response = await get_response(request)
                response["X-Request-ID"] = request.request_id
                return response
            finally:
                request_context.reset(token)
    else:

        def middleware(request):
            token = start(request)
            try:
                response = get_response(request)
                response["X-Request-ID"] = request.request_id
                return response
            finally:
                request_context.reset(token)

    return middleware
