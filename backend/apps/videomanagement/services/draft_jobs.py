"""Queue and inspect owner-bound Celery writing tasks."""

from billiard.exceptions import SoftTimeLimitExceeded, TimeLimitExceeded
from celery.result import AsyncResult
from django.core import signing
from rest_framework.exceptions import APIException, NotFound, ValidationError

from apps.videomanagement.exceptions import VideoEditConflict

SALT = "ai-draft-job-v1"
MAX_AGE = 86400
DEFAULT_TASK_ERROR = "Could not generate this draft. Please try again."


class DraftQueueUnavailable(APIException):
    status_code = 503
    default_detail = "Could not queue the draft. Please try again."


def queue_draft(user, task, **values):
    try:
        job = task.delay(str(user.pk), **values)
    except Exception as exc:
        raise DraftQueueUnavailable() from exc
    return {"id": signing.dumps([str(user.pk), job.id], salt=SALT), "status": "QUEUED"}


def _validation_message(detail):
    if not detail:
        return DEFAULT_TASK_ERROR
    if isinstance(detail, dict):
        if "detail" in detail:
            return _validation_message(detail["detail"])
        field, value = next(iter(detail.items()))
        message = _validation_message(value)
        return (
            message
            if field == "non_field_errors"
            else f"{str(field).replace('_', ' ')}: {message}"
        )
    if isinstance(detail, (list, tuple)):
        return _validation_message(detail[0])
    return str(detail)


def _task_error(error):
    if isinstance(error, (ValidationError, VideoEditConflict)):
        return _validation_message(error.detail)
    if isinstance(error, (SoftTimeLimitExceeded, TimeLimitExceeded)):
        return "Generation took too long. Please try again."
    # Provider exceptions can contain credentials, URLs or internal response data.
    return DEFAULT_TASK_ERROR


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
    if state == "FAILURE":
        return {"status": "FAILED", "error": _task_error(job.result)}
    if state == "REVOKED":
        return {
            "status": "FAILED",
            "error": "Generation was cancelled or expired. Please try again.",
        }
    return {"status": "RUNNING" if state == "STARTED" else "QUEUED"}
