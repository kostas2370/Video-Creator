"""Inspect and validate uploaded videos for caption projects."""

from rest_framework.exceptions import ValidationError

from apps.videomanagement.services.media.video_uploads import inspect_video_upload

MAX_UPLOAD_BYTES = 100 * 1024 * 1024
MAX_DURATION_SECONDS = 900


def validate_caption_upload(upload):
    if upload.size > MAX_UPLOAD_BYTES:
        raise ValidationError("Choose a video smaller than 100 MB.")
    metadata = inspect_video_upload(upload)
    if metadata["duration"] > MAX_DURATION_SECONDS:
        raise ValidationError("Choose a video up to 15 minutes long.")
    if not metadata["audio"]:
        raise ValidationError("This video has no audio to transcribe.")
    return metadata
