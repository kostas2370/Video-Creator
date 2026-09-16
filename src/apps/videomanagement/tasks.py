"""
Background jobs for the long-running parts of the pipeline.

Generation and rendering take minutes and cannot run inside a request: the proxy
times out, the worker process stays pinned for the duration, and a killed process
leaves the row stranded mid-status. Each task below owns one video and is
responsible for leaving it in a terminal status (READY / COMPLETED / FAILED)
whatever happens, so a client can poll `GET /video/{id}/` and always learn the
outcome.

Service imports are deliberately function-local: they pull in moviepy, TTS and
torch, and only the worker should pay for that at import time.
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .models import Video

logger = logging.getLogger(__name__)

#: Statuses that mean "a worker is supposed to be holding this right now".
IN_FLIGHT_STATUSES = ("GENERATION", "RENDERING")


def _mark_failed(video: Video) -> None:
    Video.objects.filter(pk=video.pk).update(status="FAILED")


@shared_task(bind=True)
def generate_video_task(self, video_id: int, **params):
    """Run AI generation for a video already created in GENERATION status."""
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
    """Run Twitch clip collection for a video already created in GENERATION status."""
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
    """Render the final mp4. `make_video` moves the video to RENDERING itself."""
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
    """Re-run scene audio and imagery for an existing video."""
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
