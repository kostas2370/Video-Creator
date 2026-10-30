"""Common checks for video imports in Clips and caption projects."""

import math
import subprocess
from pathlib import Path

from rest_framework.exceptions import ValidationError

from apps.videomanagement.utils.timing import uploaded_video_metadata


def inspect_video_upload(upload):
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
    if not math.isfinite(metadata["duration"]) or metadata["duration"] <= 0:
        raise ValidationError("Choose a video with a valid duration.")
    if not all(0 < metadata[key] <= 3840 for key in ("width", "height")):
        raise ValidationError("Choose a video with dimensions up to 3840 pixels.")
    return metadata
