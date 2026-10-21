"""Owner-bound thumbnail drafts in Celery's expiring result backend."""

import base64
from uuid import uuid4

from celery.result import AsyncResult
from django.core import signing
from rest_framework.exceptions import APIException, NotFound

SALT = "video-cover-job"


class CoverQueueUnavailable(APIException):
    status_code = 503
    default_detail = "Could not queue the thumbnail. Please try again."


def queue_cover(video, user, choices):
    from apps.videomanagement.tasks import generate_cover_task

    task_id = str(uuid4())
    try:
        generate_cover_task.apply_async(
            args=(str(video.pk), str(user.pk), choices), task_id=task_id
        )
    except Exception as exc:
        raise CoverQueueUnavailable() from exc
    return {
        "id": signing.dumps([str(video.pk), str(user.pk), task_id], salt=SALT),
        "status": "QUEUED",
    }


def cover_result(video, user, token, image=False):
    try:
        video_id, user_id, task_id = signing.loads(token, salt=SALT, max_age=86400)
    except (signing.BadSignature, ValueError, TypeError) as exc:
        raise NotFound("Thumbnail job not found or expired.") from exc
    if video_id != str(video.pk) or user_id != str(user.pk):
        raise NotFound("Thumbnail job not found.")
    job = AsyncResult(task_id)
    state = job.state
    if state == "SUCCESS":
        if image:
            return base64.b64decode(job.result["image"])
        return {"status": "SUCCEEDED"}
    if state in ("FAILURE", "REVOKED"):
        return {
            "status": "FAILED",
            "error": "Could not generate the thumbnail. Please try again. Your saved cover is unchanged.",
        }
    return {"status": "RUNNING" if state == "STARTED" else "QUEUED"}
