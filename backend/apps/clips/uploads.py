from rest_framework.exceptions import ValidationError

from apps.videomanagement.services.media.video_uploads import inspect_video_upload

MAX_UPLOAD_BYTES = 1024 * 1024 * 1024
MAX_DURATION_SECONDS = 7200


def validate_upload(upload):
    if upload.size > MAX_UPLOAD_BYTES:
        raise ValidationError("Choose a video up to 1 GB.")
    metadata = inspect_video_upload(upload)
    if metadata["duration"] > MAX_DURATION_SECONDS:
        raise ValidationError("Choose a video up to 2 hours long.")
    if not metadata["audio"]:
        raise ValidationError("Choose a video with spoken audio.")
    return metadata
