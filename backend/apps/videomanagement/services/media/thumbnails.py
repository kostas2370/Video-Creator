"""Create a small, persistent library thumbnail only when it is missing."""

import logging
import random
import subprocess
from io import BytesIO
from pathlib import Path
from threading import Lock
from uuid import uuid4
from weakref import WeakValueDictionary

from django.core.files.base import ContentFile
from PIL import Image
from rest_framework.exceptions import ValidationError

from apps.videomanagement.events import publish_update
from apps.videomanagement.models import SceneImage, Video, VideoStatus
from apps.videomanagement.utils.file_utils import check_if_video, stored_file_exists
from apps.videomanagement.utils.timing import media_timing

logger = logging.getLogger(__name__)
_locks = WeakValueDictionary()
_lock_guard = Lock()


def _thumbnail_lock(video_id):
    with _lock_guard:
        lock = _locks.get(video_id)
        if lock is None:
            lock = Lock()
            _locks[video_id] = lock
        return lock


def thumbnail_time(duration, intro=0, outro=0):
    start, end = intro, duration - outro
    if end <= start:
        start, end = 0, duration
    return start + (end - start) * random.uniform(0.35, 0.75)


def ensure_thumbnail(owned_video):
    # Coalesce requests without holding a database transaction while FFmpeg runs.
    with _thumbnail_lock(owned_video.pk):
        video = Video.objects.select_related("intro", "outro").get(pk=owned_video.pk)
        if stored_file_exists(video.cover):
            return video.cover
        if stored_file_exists(video.thumbnail):
            return video.thumbnail
        if video.status == VideoStatus.RENDERING:
            raise ValidationError(
                "The thumbnail will be available after the export finishes."
            )
        source = video.output if stored_file_exists(video.output) else None
        from_export = source is not None
        if source is None:
            visual = (
                SceneImage.objects.filter(scene__video=video)
                .exclude(file="")
                .exclude(file__isnull=True)
                .order_by("scene__position", "created_at", "id")
                .first()
            )
            if visual and stored_file_exists(visual.file):
                if not check_if_video(visual.file.name):
                    return visual.file
                source = visual.file
        if source is None:
            raise ValidationError(
                "Add a visual or export the video to create a thumbnail."
            )
        source_stat = Path(source.path).stat()
        duration = media_timing(source.path).get("duration")
        if not duration:
            raise ValidationError("This video's duration could not be read.")
        intro = (
            media_timing(video.intro.file.path).get("duration", 0)
            if from_export and video.intro and stored_file_exists(video.intro.file)
            else 0
        )
        outro = (
            media_timing(video.outro.file.path).get("duration", 0)
            if from_export and video.outro and stored_file_exists(video.outro.file)
            else 0
        )
        try:
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
                    source.path,
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
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            logger.warning("Could not create library thumbnail for video %s", video.pk)
            raise ValidationError(
                "The thumbnail could not be created. Try again later."
            ) from exc
        latest_stat = Path(source.path).stat()
        if (source_stat.st_mtime_ns, source_stat.st_size) != (
            latest_stat.st_mtime_ns,
            latest_stat.st_size,
        ):
            raise ValidationError(
                "The video changed. Try creating its thumbnail again."
            )
        previous_name = video.thumbnail.name
        video.thumbnail.save(
            f"{video.pk}-{uuid4().hex}.jpg", ContentFile(result.stdout), save=False
        )
        saved_name = video.thumbnail.name
        try:
            # Compare and save in one query: another worker or a new export may win.
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
        except Exception:
            video.thumbnail.storage.delete(saved_name)
            raise
        if not saved:
            video.thumbnail.storage.delete(saved_name)
            video.refresh_from_db()
            for image in (video.cover, video.thumbnail):
                if stored_file_exists(image):
                    return image
            raise ValidationError(
                "The video changed. Try creating its thumbnail again."
            )
        if previous_name:
            video.thumbnail.storage.delete(previous_name)
        publish_update(f"video.{video.pk}", video_id=video.pk)
        return video.thumbnail
