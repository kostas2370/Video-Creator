import re
import time
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from django.core.files import File
from pytubefix import YouTube
from rest_framework.exceptions import ValidationError

from .media import run_ffmpeg
from .uploads import MAX_DURATION_SECONDS, MAX_UPLOAD_BYTES, validate_upload


class SourceImportError(ValueError):
    pass


def youtube_url(value):
    try:
        parsed = urlsplit(value if "://" in value else "https://" + value)
        if (
            parsed.scheme not in {"https", "http"}
            or parsed.username
            or parsed.password
            or parsed.port
        ):
            raise ValueError()
        host = parsed.hostname
        parts = parsed.path.strip("/").split("/")
        if host in {"youtu.be", "www.youtu.be"} and len(parts) == 1:
            video_id = parts[0]
        elif host in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
            if parsed.path == "/watch":
                video_id = parse_qs(parsed.query).get("v", [""])[0]
            elif len(parts) == 2 and parts[0] in {"shorts", "embed"}:
                video_id = parts[1]
            else:
                raise ValueError()
        else:
            raise ValueError()
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
            raise ValueError()
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValidationError(
            "Enter a YouTube video, Shorts, or youtu.be link."
        ) from exc
    return f"https://www.youtube.com/watch?v={video_id}"


def download_youtube(project, directory):
    started, downloaded = time.monotonic(), 0

    def progress(stream, chunk, bytes_remaining):
        nonlocal downloaded
        downloaded += len(chunk)
        if downloaded > MAX_UPLOAD_BYTES:
            raise SourceImportError("This YouTube video exceeds the 1 GB import limit.")
        if time.monotonic() - started > 600:
            raise SourceImportError(
                "The YouTube download took too long. Retry or upload a file instead."
            )

    video = YouTube(project.youtube_url, on_progress_callback=progress)
    if not project.min_duration <= video.length <= MAX_DURATION_SECONDS:
        raise SourceImportError(
            "Choose a YouTube video between your minimum clip length and 2 hours."
        )
    combined = (
        video.streams.filter(progressive=True, file_extension="mp4")
        .order_by("resolution")
        .desc()
        .first()
    )
    if combined:
        streams = [combined]
    else:
        picture = next(
            (
                stream
                for stream in video.streams.filter(
                    only_video=True, file_extension="mp4"
                )
                .order_by("resolution")
                .desc()
                if int(stream.resolution.rstrip("p")) <= 1080
            ),
            None,
        )
        audio = video.streams.filter(only_audio=True).order_by("abr").desc().first()
        streams = [picture, audio] if picture and audio else []
    if not streams:
        raise SourceImportError(
            "No compatible video and audio streams are available. Upload a file instead."
        )
    if sum(stream.filesize for stream in streams) > MAX_UPLOAD_BYTES:
        raise SourceImportError("This YouTube video exceeds the 1 GB import limit.")
    paths = []
    for index, stream in enumerate(streams):
        path = stream.download(
            output_path=directory,
            filename=f"youtube-{index}.{stream.subtype}",
            timeout=30,
            max_retries=1,
        )
        if not path:
            raise SourceImportError(
                "The YouTube download did not finish. Please retry."
            )
        paths.append(Path(path))
    path = paths[0]
    if len(paths) == 2:
        path = Path(directory, "youtube.mp4")
        run_ffmpeg(
            [
                "-i",
                str(paths[0]),
                "-i",
                str(paths[1]),
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                "-movflags",
                "+faststart",
                str(path),
            ],
            timeout=600,
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
    return path, metadata, str(video.title)[:100]
