import logging
from datetime import timedelta
from celery import shared_task
from django.conf import settings
from django.core.files import File
from pathlib import Path
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.apikeysmanagement.models import Provider

from .models import IN_FLIGHT_STATUSES, Video, VideoStatus, VoiceModel, VoiceModelType, SceneCreationJob
from .utils import tts_utils

logger = logging.getLogger(__name__)

VOICE_IMPORTS = {
    Provider.ELEVENLABS: "get_voices_from_elevenlabs",
    Provider.SIXTYDB: "get_voices_from_sixtydb",
}


def _mark_failed(video_id: int) -> None:
    video = Video.objects.filter(pk=video_id).first()
    if video is None:
        return

    video.status = VideoStatus.FAILED
    video.save()


@shared_task(bind=True)
def generate_video_task(self, video_id: int, **params):
    from .services.VideoGenerationServices import generate_video

    video = Video.objects.get(pk=video_id)

    try:
        generate_video(video=video, **params)
    except Exception:
        logger.exception("Generation failed for video %s", video_id)
        _mark_failed(video_id)
        raise

    logger.info("Generation finished for video %s", video_id)
    return video_id


@shared_task(bind=True)
def generate_twitch_video_task(self, video_id: int, **params):
    from .services.TwitchGenerationService import generate_twitch_video

    video = Video.objects.get(pk=video_id)

    try:
        generate_twitch_video(video=video, **params)
    except Exception:
        logger.exception("Twitch generation failed for video %s", video_id)
        _mark_failed(video_id)
        raise

    logger.info("Twitch generation finished for video %s", video_id)
    return video_id


@shared_task(bind=True)
def resume_video_task(self, video_id: int):
    from .services.VideoGenerationServices import resume_video

    video = Video.objects.get(pk=video_id)

    try:
        resume_video(video)
    except Exception:
        logger.exception("Resume failed for video %s", video_id)
        _mark_failed(video_id)
        raise

    logger.info("Resume finished for video %s", video_id)
    return video_id


@shared_task(bind=True)
def render_video_task(self, video_id: int):
    from .utils.composer.render import make_video

    video = Video.objects.get(pk=video_id)

    try:
        make_video(video)
    except Exception:
        logger.exception("Render failed for video %s", video_id)
        _mark_failed(video_id)
        raise

    logger.info("Render finished for video %s", video_id)
    return video_id


@shared_task
def create_scene_task(job_id: int):
    from .services.SceneServices import create_scene

    # Duplicate deliveries must never create duplicate scenes.
    if not SceneCreationJob.objects.filter(pk=job_id, status="QUEUED").update(
        status="PROCESSING", updated_at=timezone.now()
    ):
        return
    job = SceneCreationJob.objects.select_related("video").get(pk=job_id)
    try:
        files = {}
        if job.upload:
            job.upload.open("rb")
            files["image"] = File(job.upload.file, name=Path(job.upload.name).name)
        create_scene(job.video, job.data, files)
    except Exception:
        logger.exception("Scene creation failed for job %s", job_id)
        failed = SceneCreationJob.objects.filter(pk=job_id, status="PROCESSING").update(
            status="FAILED", error="Could not finish adding the scene. Check available scenes before trying again.",
            updated_at=timezone.now(),
        )
        if failed:
            Video.objects.filter(pk=job.video_id, status=VideoStatus.GENERATION).update(status=job.previous_status)
        raise
    else:
        finished = SceneCreationJob.objects.filter(pk=job_id, status="PROCESSING").update(
            status="COMPLETED", updated_at=timezone.now()
        )
        if finished:
            Video.objects.filter(pk=job.video_id, status=VideoStatus.GENERATION).update(status=VideoStatus.READY)
    finally:
        if job.upload:
            job.upload.close()
            job.upload.delete()
    return job_id


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

    stalled = Video.objects.filter(status__in=IN_FLIGHT_STATUSES, updated_at__lt=cutoff)
    ids = list(stalled.values_list("pk", flat=True))

    if not ids:
        return 0

    SceneCreationJob.objects.filter(video_id__in=ids, status__in=["QUEUED", "PROCESSING"]).update(
        status="FAILED", error="Scene creation timed out. Check available scenes before trying again.",
        updated_at=timezone.now(),
    )
    for video_id in ids:
        _mark_failed(video_id)

    logger.warning("Reaped %s stalled videos: %s", len(ids), ids)

    return len(ids)


@shared_task
def update_user_voices(user_id: int, provider: str):
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

    existing_voices = VoiceModel.objects.filter(created_by=user, provider=provider)
    existing_map = {v.path: v for v in existing_voices}

    stale_paths = set(existing_map.keys()) - fetched_voice_ids
    if stale_paths:
        VoiceModel.objects.filter(
            created_by=user, provider=provider, path__in=stale_paths
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
