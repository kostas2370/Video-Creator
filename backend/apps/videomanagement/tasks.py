import logging
from contextlib import nullcontext
from datetime import timedelta
from pathlib import Path
from uuid import UUID

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.files.storage import default_storage
from django.utils import timezone

from apps.apikeysmanagement.models import Provider
from apps.videomanagement.integrations import tts as tts_utils
from apps.videomanagement.services.captions.projects import process_caption_project
from apps.videomanagement.services.media import covers
from apps.videomanagement.services.media.archive import archive_generated_cover
from apps.videomanagement.services.scenes import generation as scene_generation
from apps.videomanagement.services.scenes import visuals as scenes
from apps.videomanagement.services.scenes.jobs import scene_job
from apps.videomanagement.services.videos import generation as video_generation

from .events import publish_update
from .models import Video, VideoStatus, VoiceModel, VoiceModelType
from .serializers.models import SceneSerializer
from .utils.composer import render

logger = logging.getLogger(__name__)


@shared_task(soft_time_limit=570, time_limit=600, expires=86400)
def generate_cover_task(video_id, user_id, choices):
    video = Video.objects.select_related("created_by", "prompt").get(
        pk=video_id, created_by_id=user_id
    )
    if not video.created_by.is_active:
        raise ValueError("Account is inactive")
    image = covers.generate_cover_image(video, video.created_by, choices)
    asset = archive_generated_cover(video, image)
    return {"asset_id": str(asset.pk)}


@shared_task(soft_time_limit=1150, time_limit=1200)
def caption_project_task(project_id, token, render=False):
    process_caption_project(project_id, token, render=render)


@shared_task
def update_scene_task(scene_id, text, previous_status):
    """Save dialogue and regenerate its narration."""
    with scene_job(scene_id, previous_status) as scene:
        text = scene_generation.update_scene(text, scene)
        return {
            "text": text,
            "narration_status": SceneSerializer(scene).data["narration_status"],
        }


@shared_task
def rewrite_scene_task(scene_id, instructions, previous_status):
    """Return a dialogue draft for the user to review."""
    with scene_job(scene_id, previous_status) as scene:
        return {"text": scene_generation.generate_scene(instructions, scene)}


@shared_task
def generate_scene_image_task(scene_id, image_description, previous_status):
    """Generate and save a replacement scene visual."""
    with scene_job(scene_id, previous_status) as scene:
        from apps.videomanagement.services.scenes.shots import select_scene_shot

        options = (
            image_description
            if isinstance(image_description, dict)
            else {"image_description": image_description}
        )
        image = select_scene_shot(
            scene, options.get("scene_image"), new_shot=options.get("new_shot", False)
        )
        image.prompt = options["image_description"]
        scenes.generate_new_image(image, scene.video)
        return {"Message": "Image Scene was added successfully"}


VOICE_IMPORTS = {
    Provider.ELEVENLABS: "get_voices_from_elevenlabs",
    Provider.SIXTYDB: "get_voices_from_sixtydb",
}


def _mark_failed(video_id: str | UUID) -> None:
    video = Video.objects.filter(pk=video_id).first()
    if video is None:
        return

    video.status = VideoStatus.FAILED
    video.save()


@shared_task(bind=True)
def generate_video_task(self, video_id: str | UUID, **params):
    video = Video.objects.get(pk=video_id)

    try:
        video_generation.generate_video(video=video, **params)
    except Exception:
        logger.exception("Generation failed for video %s", video_id)
        _mark_failed(video_id)
        raise

    logger.info("Generation finished for video %s", video_id)
    return video_id


@shared_task(bind=True)
def resume_video_task(self, video_id: str | UUID):
    video = Video.objects.get(pk=video_id)

    try:
        video_generation.resume_video(video)
    except Exception:
        logger.exception("Resume failed for video %s", video_id)
        _mark_failed(video_id)
        raise

    logger.info("Resume finished for video %s", video_id)
    return video_id


@shared_task(bind=True)
def render_video_task(self, video_id: str | UUID):
    video = Video.objects.get(pk=video_id)

    try:
        render.make_video(video)
    except Exception:
        logger.exception("Render failed for video %s", video_id)
        _mark_failed(video_id)
        raise

    logger.info("Render finished for video %s", video_id)
    return video_id


@shared_task
def create_scene_task(video_id: str | UUID, data: dict, upload_path=None):
    try:
        video = Video.objects.filter(pk=video_id, status=VideoStatus.GENERATION).first()
        if video is None:
            return
        with (
            default_storage.open(upload_path, "rb") if upload_path else nullcontext()
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
        _mark_failed(video_id)
        raise
    else:
        Video.objects.filter(pk=video_id, status=VideoStatus.GENERATION).update(
            status=VideoStatus.READY
        )
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
    Anything untouched for longer than VIDEO_TASK_STALE_AFTER is declared dead.
    """
    cutoff = timezone.now() - timedelta(seconds=settings.VIDEO_TASK_STALE_AFTER)

    stalled = Video.objects.in_flight().filter(updated_at__lt=cutoff)
    ids = list(stalled.values_list("pk", flat=True))

    if not ids:
        return 0

    for video_id in ids:
        _mark_failed(video_id)

    logger.warning("Reaped %s stalled videos: %s", len(ids), ids)

    return len(ids)


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
