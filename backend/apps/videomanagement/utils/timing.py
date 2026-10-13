"""Cached media metadata for the editor's pre-render runtime estimate."""

import hashlib
import json
import math
import os
import subprocess

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import SuspiciousFileOperation

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
    narration = (scene.video.settings or {}).get("narration", True)
    speech = file_timing(scene.file).get("audio_duration") if narration else None
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
            else visual.get("duration", settings.SILENT_SCENE_SECONDS)
        )
    return {"base_duration": base, "duration": base + scene.pause_after}


def video_metadata(path):
    from fractions import Fraction

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
