from django.core.files import File
from pytubefix import YouTube
from rest_framework.exceptions import ValidationError

from apps.common.youtube import (
    SourceImportError,
    download_streams,
    youtube_url as youtube_url,
)

from .uploads import MAX_DURATION_SECONDS, MAX_UPLOAD_BYTES, validate_upload


def select_streams(video):
    combined = video.streams.filter(progressive=True, file_extension="mp4")
    pictures = video.streams.filter(only_video=True, file_extension="mp4")
    candidates = [(stream, True) for stream in combined] + [
        (stream, False) for stream in pictures
    ]
    candidates = sorted(
        (
            (stream, combined)
            for stream, combined in candidates
            if int(stream.resolution.rstrip("p")) <= 1080
        ),
        key=lambda item: (int(item[0].resolution.rstrip("p")), item[1]),
        reverse=True,
    )
    audio = None
    compatible = False
    for stream, combined in candidates:
        if combined:
            streams = [stream]
        else:
            if audio is None:
                audio = (
                    video.streams.filter(only_audio=True).order_by("abr").desc().first()
                )
            if audio is None:
                continue
            streams = [stream, audio]
        compatible = True
        if sum(stream.filesize for stream in streams) <= MAX_UPLOAD_BYTES:
            return streams
    if compatible:
        raise SourceImportError(
            "Even the lowest available resolution exceeds the 1 GB import limit. Trim the video or upload a smaller file."
        )
    raise SourceImportError(
        "No compatible video and audio streams are available. Upload a file instead."
    )


def download_youtube(project, directory):
    video = YouTube(project.youtube_url)
    if not project.min_duration <= video.length <= MAX_DURATION_SECONDS:
        raise SourceImportError(
            "Choose a YouTube video between your minimum clip length and 2 hours."
        )
    path = download_streams(select_streams(video), directory)
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
    return path, metadata, str(video.title)[:100]
