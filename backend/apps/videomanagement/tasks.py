import logging
from contextlib import nullcontext
from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.files.storage import default_storage
from django.db import transaction
from django.utils import timezone

from apps.apikeysmanagement.models import Provider
from apps.videomanagement.integrations import tts as tts_utils
from apps.videomanagement.services.captions.projects import process_caption_project
from apps.videomanagement.services.media import covers
from apps.videomanagement.services.media.archive import archive_generated_cover
from apps.videomanagement.services.scenes import generation as scene_generation
from apps.videomanagement.services.scenes import visuals as scenes
from apps.videomanagement.services.scenes.jobs import scene_job
from apps.videomanagement.services.scenes.narration import (
    update_scene as regenerate_scene_narration,
)
from apps.videomanagement.services.scenes.starting_frames import (
    animate_starting_frame,
    requires_starting_frame,
)
from apps.videomanagement.services.videos import generation as video_generation
from apps.videomanagement.services.videos.recovery import video_job_heartbeat
from video_creator.observability import current_request_id

from .events import publish_update
from .models import SceneImage, Video, VideoStatus, VoiceModel, VoiceModelType
from .serializers.models import SceneSerializer
from .utils.composer import render

logger = logging.getLogger(__name__)


@shared_task(soft_time_limit=570, time_limit=600, expires=86400)
def generate_cover_task(video_id, user_id, choices):
    video = Video.objects.select_related("created_by", "prompt").get(
        pk=video_id, created_by_id=user_id
    )
    image = covers.generate_cover_image(video, video.created_by, choices)
    asset = archive_generated_cover(video, image)
    return {"asset_id": str(asset.pk)}


@shared_task(soft_time_limit=1150, time_limit=1200)
def caption_project_task(project_id, token, render=False):
    process_caption_project(project_id, token, render=render)


@shared_task
def update_scene_task(scene_id, text, previous_status, operation_id=None):
    """Save dialogue and regenerate its narration."""
    with scene_job(scene_id, previous_status, operation_id) as scene:
        text = scene_generation.update_scene(text, scene)
        return {
            "text": text,
            "narration_status": SceneSerializer(scene).data["narration_status"],
        }


@shared_task
def generate_scene_image_task(
    scene_id, image_description, previous_status, operation_id=None
):
    """Generate and save a replacement scene visual."""
    with scene_job(scene_id, previous_status, operation_id) as scene:
        if isinstance(image_description, dict):
            try:
                animate_starting_frame(scene, image_description["asset_id"])
            except Exception:
                scene.starting_frame_context = {
                    **scene.starting_frame_context,
                    "animation_error": "Animation failed. Your starting frame and existing clip are saved. Retry when ready.",
                }
                scene.save(update_fields=["starting_frame_context"])
                raise
            scene.starting_frame_context.pop("animation_error", None)
            scene.save(update_fields=["starting_frame_context"])
            return {"Message": "Animation is ready"}
        image = scene.scene_images.first() or SceneImage.objects.create(scene=scene)
        image.prompt = image_description
        try:
            scenes.generate_new_image(image, scene.video)
        except Exception:
            if requires_starting_frame(scene.video):
                scene.refresh_from_db()
                scene.starting_frame_context = {
                    **scene.starting_frame_context,
                    "preparation_error": "Could not prepare the starting frame. Your saved media is preserved. Try again.",
                }
                scene.save(update_fields=["starting_frame_context"])
            raise
        return {"Message": "Image Scene was added successfully"}


@shared_task(soft_time_limit=1150, time_limit=1200)
def regenerate_narration_task(video_id, previous_status, operation_id=None):
    with video_job_heartbeat(video_id, operation_id) as active:
        if not active:
            return
        # Wait for the settings transaction before reading its selected voice.
        with transaction.atomic():
            video = (
                Video.objects.select_for_update()
                .filter(
                    pk=video_id,
                    status=VideoStatus.GENERATION,
                    operation_id=operation_id,
                )
                .first()
            )
            if video is None:
                return
        try:
            for scene in video.scenes.all():
                regenerate_scene_narration(scene)
        except Exception:
            _mark_failed(video_id, operation_id=operation_id)
            raise
        else:
            Video.objects.filter(
                pk=video_id, status=VideoStatus.GENERATION, operation_id=operation_id
            ).update(
                status=previous_status,
                narration_retry_status="",
                updated_at=timezone.now(),
            )
        finally:
            publish_update(f"video.{video_id}", video_id=video_id)


VOICE_IMPORTS = {
    Provider.ELEVENLABS: "get_voices_from_elevenlabs",
    Provider.SIXTYDB: "get_voices_from_sixtydb",
}


def _mark_failed(video_id: str | UUID, render_error=None, operation_id=None) -> None:
    with transaction.atomic():
        video = (
            Video.objects.select_for_update()
            .filter(pk=video_id, operation_id=operation_id)
            .first()
        )
        if video is None:
            return
        if render_error is None and video.status == VideoStatus.RENDERING:
            render_error = {
                "message": "The export stopped before it finished. Retry the export; your scenes are saved.",
                "reference": current_request_id() or uuid4().hex,
            }
        if render_error:
            logger.error(
                "Export failed for video %s. Reference: %s",
                video_id,
                render_error["reference"],
            )
        video.render_error = render_error or {}
        video.status = VideoStatus.FAILED
        video.save(update_fields=["render_error", "status", "updated_at"])


@shared_task(bind=True)
def generate_video_task(self, video_id: str | UUID, operation_id=None, **params):
    with video_job_heartbeat(video_id, operation_id) as active:
        if not active:
            return
        video = Video.objects.get(pk=video_id)

        try:
            video_generation.generate_video(video=video, **params)
        except Exception:
            logger.exception("Generation failed for video %s", video_id)
            _mark_failed(video_id, operation_id=operation_id)
            raise

        logger.info("Generation finished for video %s", video_id)
        return video_id


@shared_task(bind=True)
def resume_video_task(self, video_id: str | UUID, operation_id=None):
    with video_job_heartbeat(video_id, operation_id) as active:
        if not active:
            return
        video = Video.objects.get(pk=video_id)

        try:
            video_generation.resume_video(video)
        except Exception:
            logger.exception("Resume failed for video %s", video_id)
            _mark_failed(video_id, operation_id=operation_id)
            raise

        logger.info("Resume finished for video %s", video_id)
        return video_id


@shared_task(bind=True)
def render_video_task(self, video_id: str | UUID, operation_id=None):
    with video_job_heartbeat(video_id, operation_id) as active:
        if not active:
            return
        video = Video.objects.get(pk=video_id)
        video.render_error = {}
        video.save(update_fields=["render_error"])

        try:
            render.make_video(video)
        except Exception:
            reference = current_request_id() or uuid4().hex
            logger.exception(
                "Render failed for video %s. Reference: %s", video_id, reference
            )
            _mark_failed(
                video_id,
                operation_id=operation_id,
                render_error={
                    "message": "The export could not finish. Retry the export; your scenes and media are saved. If it fails again, share the reference with support.",
                    "reference": reference,
                },
            )
            raise

        logger.info("Render finished for video %s", video_id)
        return video_id


@shared_task
def create_scene_task(
    video_id: str | UUID, data: dict, upload_path=None, operation_id=None
):
    try:
        with video_job_heartbeat(video_id, operation_id) as active:
            if not active:
                return
            try:
                video = Video.objects.filter(
                    pk=video_id,
                    status=VideoStatus.GENERATION,
                    operation_id=operation_id,
                ).first()
                if video is None:
                    return
                with (
                    default_storage.open(upload_path, "rb")
                    if upload_path
                    else nullcontext()
                ) as upload:
                    files = (
                        {"image": File(upload, name=Path(upload_path).name)}
                        if upload_path
                        else {}
                    )
                    next_position = data.get("position") if "scenes" in data else None
                    for item in data.get("scenes", [data]):
                        if next_position is not None:
                            item = {**item, "position": next_position}
                        created = scene_generation.create_scene(video, item, files)
                        if next_position is not None:
                            next_position = created.position + 1
            except Exception:
                logger.exception("Scene creation failed for video %s", video_id)
                _mark_failed(video_id, operation_id=operation_id)
                raise
            else:
                Video.objects.filter(
                    pk=video_id,
                    status=VideoStatus.GENERATION,
                    operation_id=operation_id,
                ).update(status=VideoStatus.READY)
                publish_update(f"video.{video_id}", video_id=video_id)
    finally:
        if upload_path:
            default_storage.delete(upload_path)
    return video_id


@shared_task
def reap_stalled_videos():
    """
    Fail videos that no worker can still be working on.

    A task that dies without unwinding — OOM during an encode, a deploy, a hard
    kill — never reaches its own `except`, so the row would otherwise sit in
    GENERATION or RENDERING forever and the owner would never get an answer.
    Running jobs refresh updated_at every minute. Only projects without activity
    for VIDEO_TASK_STALE_AFTER are recovered, after rechecking under a row lock.
    """
    cutoff = timezone.now() - timedelta(seconds=settings.VIDEO_TASK_STALE_AFTER)

    stalled = Video.objects.in_flight().filter(updated_at__lt=cutoff)
    ids = list(stalled.values_list("pk", flat=True))
    recovered = []
    for video_id in ids:
        with transaction.atomic():
            video = (
                stalled.select_for_update(skip_locked=True).filter(pk=video_id).first()
            )
            if video is None:
                continue
            _mark_failed(video_id, operation_id=video.operation_id)
            recovered.append(video_id)

    if recovered:
        logger.warning("Recovered %s stalled videos: %s", len(recovered), recovered)
    return len(recovered)


@shared_task
def update_user_voices(user_id: str | UUID, provider: str):
    fetcher = VOICE_IMPORTS.get(provider)
    user = get_user_model().objects.filter(pk=user_id).first()
    if user is None:
        return 0

    try:
        if fetcher:
            voices = getattr(tts_utils, fetcher)(user=user)
        else:
            voices = tts_utils.get_voices_from_custom_provider(
                user=user, custom_provider_name=provider
            )
        if voices is None:
            return 0
        voice_id_field = "voice_id" if fetcher else "id"
    except Exception:
        logger.exception("Could not read %s voices for user %s", provider, user_id)
        raise

    # Validate the whole response before removing any previously imported voices.
    voices = [
        {
            "id": str(voice[voice_id_field]),
            "name": voice["name"],
            "sample": voice.get("preview_url", ""),
        }
        for voice in voices
    ]
    fetched_voice_ids = {voice["id"] for voice in voices}

    clone_paths = set(
        VoiceModel.objects.filter(is_cloned=True, provider=provider).values_list(
            "path", flat=True
        )
    )
    voices = [voice for voice in voices if voice["id"] not in clone_paths]
    existing_voices = VoiceModel.objects.filter(
        created_by=user, provider=provider, is_cloned=False
    )
    existing_map = {v.path: v for v in existing_voices}

    stale_paths = set(existing_map.keys()) - fetched_voice_ids
    if stale_paths:
        VoiceModel.objects.filter(
            created_by=user, provider=provider, path__in=stale_paths, is_cloned=False
        ).delete()

    added = [
        VoiceModel(
            name=voice["name"],
            provider=provider,
            type=VoiceModelType.API if fetcher else VoiceModelType.CUSTOM_API,
            path=voice["id"],
            sample=voice["sample"],
            created_by=user,
        )
        for voice in voices
        if voice["id"] not in existing_map
    ]

    updated = []
    for voice in voices:
        existing = existing_map.get(voice["id"])
        if existing and (
            existing.name != voice["name"] or existing.sample != voice["sample"]
        ):
            existing.name = voice["name"]
            existing.sample = voice["sample"]
            updated.append(existing)
    VoiceModel.objects.bulk_update(updated, ["name", "sample"])
    VoiceModel.objects.bulk_create(added)
    logger.info(
        "Imported %s and cleaned up stale voices for user %s (%s)",
        len(added),
        user_id,
        provider,
    )

    return len(added)


@shared_task(soft_time_limit=270, time_limit=300)
def purge_deleted_scenes():
    """Daily, bounded cleanup; a later run resumes any remaining backlog."""
    from apps.videomanagement.services.scenes.recovery import (
        SCENE_CLEANUP_BATCH_SIZE,
        purge_expired_scenes,
    )

    result = purge_expired_scenes()
    if result["examined"] == SCENE_CLEANUP_BATCH_SIZE and result["deleted"]:
        # Drain large backlogs in short jobs rather than leaving them until tomorrow.
        purge_deleted_scenes.apply_async(countdown=30)
    return result
