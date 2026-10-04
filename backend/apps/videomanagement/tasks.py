import logging
from datetime import timedelta
import requests
from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.apikeysmanagement.models import Provider, UserCustomTTSProvider

from .models import IN_FLIGHT_STATUSES, Video, VideoStatus, VoiceModel, VoiceModelType
from .utils import tts_utils

logger = logging.getLogger(__name__)

VOICE_IMPORTS = {
    Provider.ELEVENLABS: ("eleven_labs", "get_voices_from_labs"),
    Provider.SIXTYDB: ("60db", "get_voices_from_60db"),
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

    for video_id in ids:
        _mark_failed(video_id)

    logger.warning("Reaped %s stalled videos: %s", len(ids), ids)

    return len(ids)


@shared_task
def update_user_voices(user_id: int, provider: str):
    fetcher = VOICE_IMPORTS.get(provider, ("custom", "get_voices_from_custom_provider"))
    user = get_user_model().objects.filter(pk=user_id).first()
    if user is None:
        return 0

    try:
        voices = getattr(tts_utils, fetcher[1])(user, provider)
    except Exception:
        logger.exception("Could not read %s voices for user %s", provider, user_id)
        raise

    fetched_voice_ids = {voice["id"] for voice in voices}

    existing_voices = VoiceModel.objects.filter(created_by=user, provider=provider)
    existing_map = {v.path: v for v in existing_voices}

    stale_paths = set(existing_map.keys()) - fetched_voice_ids
    if stale_paths:
        VoiceModel.objects.filter(created_by=user, provider=provider, path__in=stale_paths).delete()

    added = [
        VoiceModel(
            name=voice["name"],
            provider=provider,
            type="API",
            path=voice["id"],
            sample=voice.get("preview_url", ""),
            created_by=user,
        )
        for voice in voices
        if voice["id"] not in existing_map
    ]

    VoiceModel.objects.bulk_create(added)
    logger.info("Imported %s and cleaned up stale voices for user %s (%s)", len(added), user_id, provider)

    return len(added)