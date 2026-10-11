"""Use Celery's existing result backend for scene jobs."""
from uuid import uuid4

from celery.result import AsyncResult
from django.core import signing
from django.utils import timezone
from rest_framework.exceptions import APIException, NotFound

from ..events import publish_update
from ..models import Video, VideoStatus
from ..permissions import SceneGenerationLimitPermission
from ..utils.cost_utils import reserve_scene_credit
from .editing import editable_video

COSTS = {"UPDATE": 0.01, "REWRITE": 0.03, "IMAGE": 0.08}
JOB_SALT = "scene-job"


class QueueUnavailable(APIException):
    status_code = 503
    default_detail = "Could not queue the scene job. Please try again."


def restore_video(video_id, previous_status):
    Video.objects.filter(pk=video_id, status=VideoStatus.GENERATION).update(
        status=previous_status, updated_at=timezone.now()
    )
    publish_update(f"video.{video_id}", video_id=video_id)


def queue_scene_job(scene, user, kind, payload):
    from ..tasks import scene_job_task

    with editable_video(scene.video_id) as video:
        previous_status = video.status
        with reserve_scene_credit(user, COSTS[kind], SceneGenerationLimitPermission.required_limit):
            video.status = VideoStatus.GENERATION
            video.save(update_fields=["status", "updated_at"])
    task_id = str(uuid4())
    try:
        scene_job_task.apply_async(
            args=(str(scene.pk), kind, payload, previous_status), task_id=task_id,
        )
    except Exception as exc:
        restore_video(video.pk, previous_status)
        raise QueueUnavailable() from exc
    publish_update(f"video.{video.pk}", video_id=video.pk)
    # Bind the result to its scene without storing another database record.
    token = signing.dumps([str(scene.pk), task_id], salt=JOB_SALT)
    return {"id": token, "status": "QUEUED"}


def scene_job_result(scene, token):
    try:
        scene_id, task_id = signing.loads(token, salt=JOB_SALT, max_age=86400)
    except signing.BadSignature as exc:
        raise NotFound("Scene job not found or expired.") from exc
    if scene_id != str(scene.pk):
        raise NotFound("Scene job not found.")
    job = AsyncResult(task_id)
    state = job.state
    if state == "SUCCESS":
        return {"status": "SUCCEEDED", "result": job.result}
    if state in ("FAILURE", "REVOKED"):
        return {"status": "FAILED", "error": "Could not finish the scene job. Please try again."}
    return {"status": "RUNNING" if state == "STARTED" else "QUEUED"}
