"""Shared YouTube video downloading using pytubefix and FFmpeg."""

import re
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


def download_streams(streams, directory):
    """Download selected streams and join separate video and audio if needed."""
    paths = []
    filename = f"youtube-{uuid4().hex}"
    for index, stream in enumerate(streams):
        path = stream.download(
            output_path=directory,
            filename=f"{filename}-{index}.{stream.subtype}",
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
            timeout=600,
        )
    return path


def download_youtube_video(url, directory, *, audio_only=False):
    """Download a YouTube video or its audio and return the path and title."""
    video = YouTube(url)
    if audio_only:
        stream = (
            video.streams.filter(only_audio=True, file_extension="mp4")
            .order_by("abr")
            .desc()
            .first()
        )
    else:
        stream = video.streams.get_highest_resolution()
    if stream is None:
        raise SourceImportError(
            "No compatible media is available. Upload a file instead."
        )
    return download_streams([stream], directory), str(video.title)
