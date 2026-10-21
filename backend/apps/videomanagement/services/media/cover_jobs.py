"""Owner-bound thumbnail drafts in Celery's expiring result backend."""

import base64
from uuid import uuid4

from celery.result import AsyncResult
from django.core import signing
from rest_framework.exceptions import NotFound

from apps.videomanagement import tasks
from apps.videomanagement.exceptions import CoverQueueUnavailable
from apps.videomanagement.models import MediaAsset
from apps.videomanagement.services.media.archive import archive_generated_cover
from apps.videomanagement.utils.file_utils import stored_file_exists

SALT = "video-cover-job"


def queue_cover(video, user, choices):
    task_id = str(uuid4())
    try:
        tasks.generate_cover_task.apply_async(
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
    if state in ("FAILURE", "REVOKED"):
        return {
            "status": "FAILED",
            "error": "Could not generate the thumbnail. Please try again. Your saved cover is unchanged.",
        }
    if state != "SUCCESS":
        return {"status": "RUNNING" if state == "STARTED" else "QUEUED"}

    asset_id = job.result.get("asset_id")
    if asset_id:
        asset = MediaAsset.objects.filter(pk=asset_id, created_by=user).first()
    else:
        # Archive drafts from jobs started before the update as they are retrieved.
        asset = archive_generated_cover(video, base64.b64decode(job.result["image"]))
    if not asset or not stored_file_exists(asset.file):
        return {
            "status": "FAILED",
            "error": "This thumbnail was removed from your Media Library.",
        }
    if not image:
        return {"status": "SUCCEEDED", "asset_id": str(asset.pk)}
    with asset.file.open("rb") as source:
        return source.read()
