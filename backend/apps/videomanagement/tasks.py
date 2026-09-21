import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.apikeysmanagement.models import Provider

from .models import Video, VoiceModel
from .utils import tts_utils

logger = logging.getLogger(__name__)

IN_FLIGHT_STATUSES = ("GENERATION", "RENDERING")

VOICE_IMPORTS = {
    Provider.ELEVENLABS: ("eleven_labs", "get_voices_from_labs"),
    Provider.SIXTYDB: ("60db", "get_voices_from_60db"),
}


def _mark_failed(video: Video) -> None:
    Video.objects.filter(pk=video.pk).update(status="FAILED")


@shared_task(bind=True)
def generate_video_task(self, video_id: int, **params):
    from .services.VideoGenerationServices import generate_video

    video = Video.objects.get(pk=video_id)

    try:
        generate_video(video=video, **params)
    except Exception:
        logger.exception("Generation failed for video %s", video_id)
        _mark_failed(video)
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
        _mark_failed(video)
        raise

    logger.info("Twitch generation finished for video %s", video_id)
    return video_id


@shared_task(bind=True)
def render_video_task(self, video_id: int):
    from .utils.video_utils import make_video

    video = Video.objects.get(pk=video_id)

    try:
        make_video(video)
    except Exception:
        logger.exception("Render failed for video %s", video_id)
        _mark_failed(video)
        raise

    logger.info("Render finished for video %s", video_id)
    return video_id


@shared_task(bind=True)
def regenerate_video_task(self, video_id: int):
    from .services.VideoServices import video_regenerate

    video = Video.objects.get(pk=video_id)

    try:
        video_regenerate(video)
    except Exception:
        logger.exception("Regeneration failed for video %s", video_id)
        _mark_failed(video)
        raise

    logger.info("Regeneration finished for video %s", video_id)
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

    stalled.update(status="FAILED")
    logger.warning("Reaped %s stalled videos: %s", len(ids), ids)

    return len(ids)


@shared_task
def import_user_voices(user_id: int, provider: str):
    provider_name, fetcher = VOICE_IMPORTS[provider]
    user = get_user_model().objects.filter(pk=user_id).first()
    if user is None:
        return 0

    try:
        voices = getattr(tts_utils, fetcher)(user)
    except Exception:
        logger.exception("Could not read %s voices for user %s", provider, user_id)
        raise

    existing = set(
        VoiceModel.objects.filter(created_by=user, provider=provider_name).values_list(
            "path", flat=True
        )
    )

    added = [
        VoiceModel(
            name=voice["name"],
            provider=provider_name,
            type="API",
            path=voice["voice_id"],
            sample=voice.get("preview_url", ""),
            created_by=user,
        )
        for voice in voices
        if voice["voice_id"] not in existing
    ]

    VoiceModel.objects.bulk_create(added)
    logger.info("Imported %s %s voices for user %s", len(added), provider, user_id)

    return len(added)
