from django.core.files import File
from rest_framework.exceptions import ValidationError

from apps.common.youtube import (
    SourceImportError,
    download_youtube_video,
    youtube_url as youtube_url,
    select_streams as select_youtube_streams,
)

from .uploads import MAX_DURATION_SECONDS, MAX_UPLOAD_BYTES, validate_upload


def select_streams(video):
    return select_youtube_streams(
        video, max_bytes=MAX_UPLOAD_BYTES, max_resolution=1080
    )


def download_youtube(project, directory):
    path, title = download_youtube_video(
        project.youtube_url,
        directory,
        min_duration=project.min_duration,
        max_duration=MAX_DURATION_SECONDS,
        max_bytes=MAX_UPLOAD_BYTES,
        max_resolution=1080,
    )
    with path.open("rb") as file:
        try:
            metadata = validate_upload(File(file))
        except ValidationError as exc:
            raise SourceImportError(
                "The imported video exceeds the limits or has no usable audio. Try a different source."
            ) from exc
    if metadata["duration"] < project.min_duration:
        raise SourceImportError(
            "This video is shorter than the requested minimum clip length."
        )
    return path, metadata, title[:100]
