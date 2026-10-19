"""Inspect editor uploads once, preserving their position for storage."""

import subprocess
from pathlib import Path

from PIL import Image
from rest_framework.exceptions import ValidationError

from apps.videomanagement.models import MediaAsset
from apps.videomanagement.utils.file_utils import check_if_image, check_if_video
from apps.videomanagement.utils.timing import (
    media_timing,
    uploaded_media_path,
    uploaded_video_metadata,
)

MAX_UPLOAD_BYTES = 100 * 1024 * 1024
MAX_DURATION_SECONDS = 900
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}


def inspect_media_upload(upload, *, allow_audio=False, max_image_pixels=None):
    if upload.size > MAX_UPLOAD_BYTES:
        raise ValidationError("Choose media smaller than 100 MB.")
    try:
        if check_if_image(upload.name):
            with Image.open(upload) as image:
                if max_image_pixels and image.width * image.height > max_image_pixels:
                    raise ValidationError(
                        f"Use an image with at most {max_image_pixels:,} pixels."
                    )
                image.verify()
            return {"kind": MediaAsset.Kind.IMAGE}
        if check_if_video(upload.name):
            metadata = uploaded_video_metadata(upload)
            kind = MediaAsset.Kind.VIDEO
            duration = metadata["duration"]
        elif allow_audio and Path(upload.name).suffix.lower() in AUDIO_EXTENSIONS:
            with uploaded_media_path(upload) as path:
                metadata = media_timing(path)
            kind = MediaAsset.Kind.AUDIO
            duration = metadata.get("audio_duration")
        else:
            formats = "JPEG, PNG, WebP, MP4, MOV, WebM, AVI, M4V"
            if allow_audio:
                formats += ", MP3, WAV, M4A, AAC, OGG, or FLAC"
            raise ValidationError(f"Choose a {formats} file.")
        if not duration or duration > MAX_DURATION_SECONDS:
            raise ValidationError("Choose playable media up to 15 minutes long.")
        return {"kind": kind, "duration": duration}
    except (
        OSError,
        ValueError,
        KeyError,
        StopIteration,
        Image.DecompressionBombError,
        subprocess.SubprocessError,
    ) as exc:
        raise ValidationError(
            "Could not read this media. Choose another file."
        ) from exc
    finally:
        upload.seek(0)


def validate_visual(upload):
    inspect_media_upload(upload)
    return upload
