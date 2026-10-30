"""Shared YouTube video downloading using pytubefix and FFmpeg."""

import re
import time
from pathlib import Path
from uuid import uuid4
from urllib.parse import parse_qs, urlsplit

from pytubefix import YouTube
from rest_framework.exceptions import ValidationError

from apps.common.media import run_ffmpeg


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


def select_streams(video, *, max_bytes=None, max_resolution=None):
    combined = video.streams.filter(progressive=True, file_extension="mp4")
    pictures = video.streams.filter(only_video=True, file_extension="mp4")
    candidates = [(stream, True) for stream in combined] + [
        (stream, False) for stream in pictures
    ]
    candidates = sorted(
        (
            (stream, combined)
            for stream, combined in candidates
            if max_resolution is None
            or int(stream.resolution.rstrip("p")) <= max_resolution
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
        if max_bytes is None or sum(stream.filesize for stream in streams) <= max_bytes:
            return streams
    if compatible:
        raise SourceImportError(
            "Even the lowest available resolution exceeds the configured import limit. Trim the video or upload a smaller file."
        )
    raise SourceImportError(
        "No compatible video and audio streams are available. Upload a file instead."
    )


def download_youtube_video(
    url,
    directory,
    *,
    min_duration=0,
    max_duration=None,
    max_bytes=None,
    max_resolution=None,
    timeout=600,
    audio_only=False,
):
    """Download YouTube video or audio and return its path and title.

    Callers supply import limits and validate the downloaded media as needed.
    """
    started, downloaded = time.monotonic(), 0

    def progress(stream, chunk, bytes_remaining):
        nonlocal downloaded
        downloaded += len(chunk)
        if max_bytes is not None and downloaded > max_bytes:
            raise SourceImportError(
                "This YouTube video exceeds the configured import limit."
            )
        if time.monotonic() - started > timeout:
            raise SourceImportError(
                "The YouTube download took too long. Retry or upload a file instead."
            )

    video = YouTube(url, on_progress_callback=progress)
    if video.length < min_duration or (
        max_duration is not None and video.length > max_duration
    ):
        raise SourceImportError(
            "Choose a YouTube video within the allowed duration range."
        )
    if audio_only:
        audio = (
            video.streams.filter(only_audio=True, file_extension="mp4")
            .order_by("abr")
            .desc()
        )
        streams = next(
            (
                [stream]
                for stream in audio
                if max_bytes is None or stream.filesize <= max_bytes
            ),
            None,
        )
        if streams is None:
            raise SourceImportError(
                "No compatible audio fits the import limit. Upload an audio file instead."
            )
    else:
        streams = select_streams(
            video, max_bytes=max_bytes, max_resolution=max_resolution
        )
    paths = []
    filename = f"youtube-{uuid4().hex}"
    for index, stream in enumerate(streams):
        path = stream.download(
            output_path=directory,
            filename=f"{filename}-{index}.{'m4a' if audio_only else stream.subtype}",
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
        path = Path(directory, f"{filename}.mp4")
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
            timeout=timeout,
        )
    return path, str(video.title)
