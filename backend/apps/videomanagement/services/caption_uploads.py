"""Inspect and validate uploaded videos for caption projects."""
import subprocess
from pathlib import Path

from rest_framework.exceptions import ValidationError

from ..utils.timing import uploaded_video_metadata

MAX_UPLOAD_BYTES = 100 * 1024 * 1024
MAX_DURATION_SECONDS = 900
MAX_DIMENSION_PIXELS = 3840
CAPTION_VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".m4v"}


def validate_caption_upload(upload):
    if upload.size > MAX_UPLOAD_BYTES:
        raise ValidationError("Choose a video smaller than 100 MB.")
    if Path(upload.name).suffix.lower() not in CAPTION_VIDEO_EXTENSIONS:
        raise ValidationError("Choose an MP4, MOV, WebM, or M4V video.")
    try:
        metadata = uploaded_video_metadata(upload)
    except (OSError, ValueError, KeyError, StopIteration, subprocess.SubprocessError) as exc:
        raise ValidationError("Could not read this video. Try another file.") from exc
    if metadata["duration"] > MAX_DURATION_SECONDS:
        raise ValidationError("Choose a video up to 15 minutes long.")
    if not metadata["audio"]:
        raise ValidationError("This video has no audio to transcribe.")
    if not all(0 < metadata[key] <= MAX_DIMENSION_PIXELS for key in ("width", "height")):
        raise ValidationError("Choose a video with dimensions up to 3840 pixels.")
    return metadata
