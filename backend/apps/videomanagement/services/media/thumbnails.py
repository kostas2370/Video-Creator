"""Create a small, persistent library thumbnail only when it is missing."""

import logging
import random
import subprocess
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from django.core.files.base import ContentFile
from PIL import Image
from rest_framework.exceptions import ValidationError

from apps.videomanagement.events import publish_update
from apps.videomanagement.models import SceneImage, Video, VideoStatus
from apps.videomanagement.utils.file_utils import check_if_video, stored_file_exists
from apps.videomanagement.utils.timing import file_timing, media_timing

logger = logging.getLogger(__name__)
CHANGED_MESSAGE = "The video changed. Try creating its thumbnail again."


def thumbnail_time(duration, intro=0, outro=0):
    start, end = intro, duration - outro
    if end <= start:
        start, end = 0, duration
    return start + (end - start) * random.uniform(0.35, 0.75)


def _existing_image(video):
    for image in (video.cover, video.thumbnail):
        if stored_file_exists(image):
            return image
    return None


def _thumbnail_source(video):
    if stored_file_exists(video.output):
        return video.output
    visual = (
        SceneImage.objects.select_related("asset")
        .filter(scene__video=video, scene__archived_at__isnull=True)
        .exclude(asset__file="")
        .exclude(asset__file__isnull=True)
        .order_by("scene__position", "created_at", "id")
        .first()
    )
    if visual and stored_file_exists(visual.file):
        return visual.file
    raise ValidationError("Add a visual or export the video to create a thumbnail.")


def _create_thumbnail(video, source):
    try:
        path = Path(source.path)
        before = path.stat()
        duration = media_timing(path).get("duration")
        if not duration:
            raise ValidationError("This video's duration could not be read.")
        intro, outro = (
            tuple(
                file_timing(asset.file if asset else None).get("duration", 0)
                for asset in (video.intro, video.outro)
            )
            if source == video.output
            else (0, 0)
        )
        result = subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-nostdin",
                "-threads",
                "1",
                "-ss",
                str(thumbnail_time(duration, intro, outro)),
                "-i",
                str(path),
                "-frames:v",
                "1",
                "-vf",
                "scale='min(640,iw)':'min(640,ih)':force_original_aspect_ratio=decrease",
                "-q:v",
                "4",
                "-threads",
                "1",
                "-f",
                "image2pipe",
                "-vcodec",
                "mjpeg",
                "pipe:1",
            ],
            capture_output=True,
            check=True,
            timeout=20,
        )
        Image.open(BytesIO(result.stdout)).verify()
        after = path.stat()
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        logger.warning("Could not create library thumbnail for video %s", video.pk)
        raise ValidationError(
            "The thumbnail could not be created. Try again later."
        ) from exc
    if (before.st_mtime_ns, before.st_size) != (after.st_mtime_ns, after.st_size):
        raise ValidationError(CHANGED_MESSAGE)
    return ContentFile(result.stdout)


def _save_thumbnail(video, image):
    previous_name = video.thumbnail.name
    video.thumbnail.save(f"{video.pk}-{uuid4().hex}.jpg", image, save=False)
    saved_name = video.thumbnail.name
    saved = False
    try:
        # Do not overwrite another request's image or an export in progress.
        saved = (
            Video.objects.filter(
                pk=video.pk,
                thumbnail=previous_name,
                cover=video.cover.name,
                output=video.output.name,
            )
            .exclude(status=VideoStatus.RENDERING)
            .update(thumbnail=saved_name)
        )
    finally:
        if not saved:
            video.thumbnail.storage.delete(saved_name)
    if not saved:
        video.refresh_from_db()
        existing = _existing_image(video)
        if existing:
            return existing
        raise ValidationError(CHANGED_MESSAGE)
    if previous_name:
        video.thumbnail.storage.delete(previous_name)
    publish_update(f"video.{video.pk}", video_id=video.pk)
    return video.thumbnail


def ensure_thumbnail(owned_video):
    video = Video.objects.select_related("intro", "outro").get(pk=owned_video.pk)
    existing = _existing_image(video)
    if existing:
        return existing
    if video.status == VideoStatus.RENDERING:
        raise ValidationError(
            "The thumbnail will be available after the export finishes."
        )
    source = _thumbnail_source(video)
    if not check_if_video(source.name):
        return source
    return _save_thumbnail(video, _create_thumbnail(video, source))
