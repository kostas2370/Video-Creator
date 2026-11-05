"""Recoverable, owner-bound AI drafts using the existing Celery result backend."""

from uuid import uuid4

from celery.result import AsyncResult
from django.core import signing
from rest_framework.exceptions import APIException, NotFound
from rest_framework.response import Response

from .draft_handlers import get_handler

SALT = "ai-draft-job-v1"
MAX_AGE = 86400


def draft_response(user, handler, **values):
    return Response(
        queue_draft(user, handler, values),
        status=202,
        headers={"Cache-Control": "no-store"},
    )


class DraftQueueUnavailable(APIException):
    status_code = 503
    default_detail = "Could not queue the draft. Please try again."


def queue_draft(user, handler, values):
    from apps.videomanagement.tasks import draft_ai_task

    operation = handler.__name__
    if get_handler(operation) is not handler:
        raise ValueError("Unregistered draft handler")
    task_id = str(uuid4())
    try:
        draft_ai_task.apply_async(
            args=(str(user.pk), operation, values), task_id=task_id
        )
    except Exception as exc:
        raise DraftQueueUnavailable() from exc
    return {"id": signing.dumps([str(user.pk), task_id], salt=SALT), "status": "QUEUED"}


def draft_result(user, token):
    try:
        owner_id, task_id = signing.loads(token, salt=SALT, max_age=MAX_AGE)
    except (signing.BadSignature, ValueError, TypeError) as exc:
        raise NotFound("Draft job not found or expired.") from exc
    if owner_id != str(user.pk):
        raise NotFound("Draft job not found.")
    job = AsyncResult(task_id)
    state = job.state
    if state == "SUCCESS":
        result = job.result
        if result.get("ok"):
            return {"status": "SUCCEEDED", "result": result["data"]}
        return {
            "status": "FAILED",
            "error": result.get("message", "Could not generate this draft."),
        }
    if state in ("FAILURE", "REVOKED"):
        return {
            "status": "FAILED",
            "error": "Could not generate this draft. Please try again.",
        }
    return {"status": "RUNNING" if state == "STARTED" else "QUEUED"}
