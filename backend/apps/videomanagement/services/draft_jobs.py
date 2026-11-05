"""Recoverable, owner-bound AI drafts using the existing Celery result backend."""

from celery.result import AsyncResult
from django.core import signing
from rest_framework.exceptions import APIException, NotFound

SALT = "ai-draft-job-v1"
MAX_AGE = 86400


class DraftQueueUnavailable(APIException):
    status_code = 503
    default_detail = "Could not queue the draft. Please try again."


def queue_draft(user, task, **values):
    try:
        job = task.delay(str(user.pk), **values)
    except Exception as exc:
        raise DraftQueueUnavailable() from exc
    return {"id": signing.dumps([str(user.pk), job.id], salt=SALT), "status": "QUEUED"}


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
        return {"status": "SUCCEEDED", "result": job.result}
    if state in ("FAILURE", "REVOKED"):
        return {
            "status": "FAILED",
            "error": "Could not generate this draft. Please try again.",
        }
    return {"status": "RUNNING" if state == "STARTED" else "QUEUED"}
