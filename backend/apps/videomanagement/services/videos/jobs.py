from pathlib import Path
from uuid import uuid4

from django.core.files.storage import default_storage
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.videomanagement import tasks
from apps.videomanagement.events import publish_update
from apps.videomanagement.exceptions import (
    GenerationQueueUnavailable,
    VideoEditConflict,
)
from apps.videomanagement.models import Video, VideoStatus, VideoType
from apps.videomanagement.integrations.llm import script_errors
from apps.videomanagement.integrations.visuals.registry import ImageProviderRegistry
from apps.videomanagement.services.videos.generation import create_pending_video


def queue_video_generation(*, created_by, reference_image=None, **params):
    video = create_pending_video(
        message=params["message"],
        created_by=created_by,
        video_type="AI",
        genre=params.get("genre"),
    )
    if params.get("review_script"):
        video.settings = {"generation_params": {**params, "review_script": False}}
        video.save(update_fields=["settings"])

    try:
        if reference_image:
            # The worker needs the reference path before dispatch.
            video.reference_image.save(
                reference_image.name, reference_image, save=False
            )
            Video.objects.filter(pk=video.pk).update(
                reference_image=video.reference_image.name
            )
        tasks.generate_video_task.delay(video_id=video.id, **params)
    except Exception as exc:
        video.reference_image.delete(save=False)
        video.reference_image = ""
        video.status = VideoStatus.FAILED
        video.save(update_fields=["reference_image", "status"])
        raise GenerationQueueUnavailable() from exc

    return video


def _dispatch_video_job(video, previous_status, task, **params):
    claimed_at, claimed_status = video.updated_at, video.status
    try:
        task.delay(video_id=video.pk, **params)
    except Exception as exc:
        Video.objects.filter(
            pk=video.pk, status=claimed_status, updated_at=claimed_at
        ).update(
            status=previous_status,
            updated_at=timezone.now(),
        )
        publish_update(f"video.{video.pk}", video_id=video.pk)
        raise GenerationQueueUnavailable(
            "Could not queue processing. Your project is saved. Please try again."
        ) from exc
    publish_update(f"video.{video.pk}", video_id=video.pk)
    video.refresh_from_db()
    return video


def queue_render(video):
    with transaction.atomic():
        video = Video.objects.select_for_update().get(pk=video.pk)
        if video.status not in (VideoStatus.READY, VideoStatus.COMPLETED):
            raise VideoEditConflict(
                {
                    "message": f"Video with id {video.pk} is {video.status} and cannot be rendered yet"
                }
            )
        if video.video_type == VideoType.MANUAL and not video.scenes.exists():
            raise ValidationError("Add a scene before rendering your video.")
        previous_status = video.status
        video.status = VideoStatus.RENDERING
        video.save(update_fields=["status", "updated_at"])
    return _dispatch_video_job(video, previous_status, tasks.render_video_task)


def queue_resume(video):
    with transaction.atomic():
        video = Video.objects.select_for_update().get(pk=video.pk)
        if video.video_type == VideoType.MANUAL:
            raise VideoEditConflict(
                "Manual projects do not need AI generation. Edit your scenes and render again."
            )
        if not video.gpt_answer or not video.dir_name:
            raise VideoEditConflict(
                {
                    "message": f"Video with id {video.pk} never got a script, so there is nothing to carry on from. Generate it again."
                }
            )
        if video.status not in (VideoStatus.FAILED, VideoStatus.READY):
            raise VideoEditConflict(
                {
                    "message": f"Video with id {video.pk} is {video.status} and has nothing to resume yet"
                }
            )
        previous_status = video.status
        video.status = VideoStatus.GENERATION
        video.save(update_fields=["status", "updated_at"])
    return _dispatch_video_job(video, previous_status, tasks.resume_video_task)


def approve_script(video, storyboard):
    with transaction.atomic():
        video = Video.objects.select_for_update().get(pk=video.pk)
        if video.status != VideoStatus.REVIEW:
            raise VideoEditConflict("This video is not awaiting review.")
        params = (video.settings or {}).get("generation_params")
        if not params:
            raise VideoEditConflict("Generation settings are missing.")
        if params.get("ai_scene_editing"):
            errors = script_errors(
                storyboard, narration=params.get("narration", True),
                scene_count=params.get("scene_count"), ai_scene_editing=True,
                video_provider=ImageProviderRegistry.is_video(
                    params.get("provider"), user=video.created_by,
                    mode=params.get("image_mode", "WEB"),
                ),
            )
            if errors:
                raise ValidationError({"scenes": errors})
        video.gpt_answer = dict(storyboard)
        video.title = storyboard["title"]
        video.status = VideoStatus.GENERATION
        video.save()
    return _dispatch_video_job(
        video, VideoStatus.REVIEW, tasks.generate_video_task, **params
    )


def queue_scene_creation(video, data, upload=None):
    if "scenes" in data and upload:
        raise ValidationError("Upload a visual when adding a single scene.")
    with transaction.atomic():
        video = Video.objects.select_for_update().get(pk=video.pk)
        if video.status not in (
            VideoStatus.READY,
            VideoStatus.COMPLETED,
            VideoStatus.FAILED,
        ):
            raise VideoEditConflict()
        previous_status = video.status
        video.status = VideoStatus.GENERATION
        video.save(update_fields=["status", "updated_at"])
    upload_path = None
    claimed_at = video.updated_at
    try:
        if upload:
            upload_path = default_storage.save(
                f"media/scene_uploads/{uuid4().hex}/{Path(upload.name).name}", upload
            )
        tasks.create_scene_task.delay(video.pk, dict(data), upload_path)
    except Exception as exc:
        Video.objects.filter(
            pk=video.pk, status=VideoStatus.GENERATION, updated_at=claimed_at
        ).update(status=previous_status, updated_at=timezone.now())
        if upload_path:
            default_storage.delete(upload_path)
        publish_update(f"video.{video.pk}", video_id=video.pk)
        raise GenerationQueueUnavailable(
            "Could not queue the scene. Please try again."
        ) from exc
    publish_update(f"video.{video.pk}", video_id=video.pk)
