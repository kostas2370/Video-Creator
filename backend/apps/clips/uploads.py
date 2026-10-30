import math
import subprocess
from pathlib import Path

from rest_framework.exceptions import ValidationError

from apps.videomanagement.utils.timing import uploaded_video_metadata


MAX_UPLOAD_BYTES = 1024 * 1024 * 1024
MAX_DURATION_SECONDS = 7200


def validate_upload(upload):
    if upload.size > MAX_UPLOAD_BYTES:
        raise ValidationError("Choose a video up to 1 GB.")
    if Path(upload.name).suffix.lower() not in {".mp4", ".mov", ".webm", ".m4v"}:
        raise ValidationError("Choose an MP4, MOV, WebM, or M4V video.")
    try:
        metadata = uploaded_video_metadata(upload)
    except (
        OSError,
        ValueError,
        KeyError,
        StopIteration,
        subprocess.SubprocessError,
    ) as exc:
        raise ValidationError("Could not read this video. Try another file.") from exc
    if (
        not math.isfinite(metadata["duration"])
        or not 0 < metadata["duration"] <= MAX_DURATION_SECONDS
    ):
        raise ValidationError("Choose a video up to 2 hours long.")
    if not metadata["audio"]:
        raise ValidationError("Choose a video with spoken audio.")
    if not all(0 < metadata[key] <= 3840 for key in ("width", "height")):
        raise ValidationError("Choose a video with dimensions up to 3840 pixels.")
    return metadata
