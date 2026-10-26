"""Cached media metadata for the editor's pre-render runtime estimate."""

import hashlib
import json
import math
import os
import subprocess
import tempfile
from contextlib import contextmanager
from fractions import Fraction
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import SuspiciousFileOperation

from .audio_editing import (
    duration_override,
    edited_duration,
    narration_enabled,
    narration_file,
)
from .file_utils import check_if_video


def media_timing(path):
    key = None
    try:
        stat = os.stat(path)
        identity = f"{path}:{stat.st_size}:{stat.st_mtime_ns}"
        key = "media-timing:v2:" + hashlib.sha256(identity.encode()).hexdigest()
        cached = cache.get(key)
        if cached is not None:
            return cached
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration:stream=codec_type",
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
        data = json.loads(result.stdout)
        duration = round(float(data["format"]["duration"]), 2)
        if not math.isfinite(duration) or duration <= 0:
            return {}
        audio = [
            stream
            for stream in data.get("streams", [])
            if stream.get("codec_type") == "audio"
        ]
        audio_duration = duration if audio else None
        value = {"duration": duration, "audio_duration": audio_duration}
        cache.set(key, value, 3600)
        return value
    except (OSError, TypeError, ValueError, KeyError, subprocess.SubprocessError):
        if key:
            cache.set(key, {}, 60)
        return {}


def file_timing(field):
    try:
        return media_timing(field.path) if field else {}
    except (ValueError, SuspiciousFileOperation):
        return {}


def scene_timing(scene, image=None):
    narration = narration_enabled(scene)
    silent_duration = (
        5
        if getattr(scene.video, "video_type", None) == "MANUAL"
        else settings.SILENT_SCENE_SECONDS
    )
    speech = (
        edited_duration(scene, file_timing(narration_file(scene)).get("audio_duration"))
        if narration
        else None
    )
    visual = (
        file_timing(image.file)
        if image and image.file and check_if_video(image.file.name)
        else {}
    )
    clip_audio = visual.get("audio_duration") if image and image.with_audio else None
    durations = [value for value in (speech, clip_audio) if value is not None]
    if narration:
        blank = media_timing("assets/blank.wav").get("duration", 1)
        base = max(durations) if durations else blank
        if image and scene.is_last and not image.with_audio and durations:
            base += 2 * blank
    else:
        base = (
            clip_audio
            if clip_audio is not None
            else visual.get("duration", silent_duration)
        )
    images = list(scene.scene_images.all())
    if len(images) > 1 or "visual_track_duration" in (
        getattr(scene, "audio_settings", None) or {}
    ):
        if speech is not None:
            base = speech
            if scene.is_last and not any(row.with_audio for row in images):
                base += 2 * media_timing("assets/blank.wav").get("duration", 1)
        else:
            base = (scene.audio_settings or {}).get("visual_track_duration", base)
    override = duration_override(scene)
    if override is not None:
        base = override
    return {"base_duration": base, "duration": base + scene.pause_after}


def video_metadata(path):
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=codec_type,width,height,avg_frame_rate",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )
    data = json.loads(result.stdout)
    stream = next(
        stream for stream in data["streams"] if stream["codec_type"] == "video"
    )
    duration = float(data["format"]["duration"])
    try:
        fps = float(Fraction(stream["avg_frame_rate"]))
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError("Invalid video frame rate") from exc
    if not math.isfinite(duration) or duration <= 0 or fps <= 0:
        raise ValueError("Invalid video timing")
    return {
        "duration": duration,
        "fps": fps,
        "width": stream["width"],
        "height": stream["height"],
        "audio": any(stream["codec_type"] == "audio" for stream in data["streams"]),
    }


@contextmanager
def uploaded_media_path(upload):
    """Expose upload bytes to media tools and always rewind before storage saves."""
    try:
        with tempfile.NamedTemporaryFile(
            suffix=Path(upload.name).suffix.lower()
        ) as temporary:
            for chunk in upload.chunks():
                temporary.write(chunk)
            temporary.flush()
            yield temporary.name
    finally:
        upload.seek(0)


def uploaded_video_metadata(upload):
    with uploaded_media_path(upload) as path:
        return video_metadata(path)
