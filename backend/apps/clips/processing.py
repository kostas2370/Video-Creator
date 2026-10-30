import logging
import math
import tempfile
from pathlib import Path

from django.core.files import File
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.videomanagement.services.captions.transcription import transcribe_audio
from apps.videomanagement.utils.captions.styles import PROJECT_STYLE_DEFAULTS
from apps.videomanagement.utils.timing import video_metadata

from .choices import ClipProjectStatus
from .constants import MAX_CLIPS_PER_PROJECT
from .events import update_jobs
from .highlights import overlapping, suggest_clips
from .media import run_ffmpeg
from .models import Clip, ClipProject
from .services import clip_words
from .transcripts import reuse_transcript, source_key, validate_range
from .youtube import SourceImportError, download_youtube

logger = logging.getLogger(__name__)
CHUNK_SECONDS = 600


def make_preview(project, directory):
    path = Path(directory, "preview.mp4")
    run_ffmpeg(
        [
            "-i",
            project.source.path,
            "-map",
            "0:v:0",
            "-map",
            "0:a:0",
            "-vf",
            "scale=trunc(iw*min(1\\,540/ih)/2)*2:trunc(ih*min(1\\,540/ih)/2)*2,setsar=1",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-crf",
            "28",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "64k",
            "-movflags",
            "+faststart",
            str(path),
        ]
    )
    return path


def transcribe_source(project, rows, directory):
    parts = list(project.transcript_parts)
    for index in range(
        len(parts),
        math.ceil((project.range_stop - project.range_start) / CHUNK_SECONDS),
    ):
        offset = project.range_start + index * CHUNK_SECONDS
        if not rows.filter(status=ClipProjectStatus.TRANSCRIBING).exists():
            return None
        start = max(project.range_start, offset - 2)
        end = min(project.range_stop, offset + CHUNK_SECONDS + 2)
        path = Path(directory, f"part-{index}.mp3")
        run_ffmpeg(
            [
                "-ss",
                str(start),
                "-i",
                project.source.path,
                "-t",
                str(end - start),
                "-map",
                "0:a:0",
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-b:a",
                "64k",
                str(path),
            ]
        )
        with tempfile.TemporaryDirectory(dir=directory) as chunk_directory:
            local_words = transcribe_audio(
                path, project.created_by, end - start, chunk_directory
            )
        adjusted = []
        for word in local_words:
            word_start, word_end = (
                word["start"] + start,
                min(project.range_stop, word["end"] + start),
            )
            midpoint = (word_start + word_end) / 2
            if offset <= midpoint < min(project.range_stop, offset + CHUNK_SECONDS):
                adjusted.append(
                    {
                        "text": word["text"],
                        "start": round(word_start, 4),
                        "end": round(word_end, 4),
                    }
                )
        parts.append(adjusted)
        if not update_jobs(
            rows.filter(status=ClipProjectStatus.TRANSCRIBING),
            transcript_parts=parts,
            updated_at=timezone.now(),
        ):
            return None
    words, previous_end = [], 0
    for part in parts:
        for word in part:
            start = max(previous_end, word["start"])
            if word["end"] > start:
                words.append({**word, "start": start})
                previous_end = word["end"]
    return words


def process_project(project_id, token):
    rows = ClipProject.objects.filter(pk=project_id, job_id=token)
    project = (
        rows.filter(status=ClipProjectStatus.QUEUED)
        .select_related("created_by")
        .first()
    )
    if project is None:
        return
    initial = (
        ClipProjectStatus.DOWNLOADING
        if project.youtube_url and not project.source
        else ClipProjectStatus.TRANSCRIBING
    )
    if not update_jobs(
        rows.filter(status=ClipProjectStatus.QUEUED),
        status=initial,
        updated_at=timezone.now(),
    ):
        return
    try:
        if not project.created_by.is_active:
            raise ValueError("Inactive account")
        with tempfile.TemporaryDirectory(prefix="clips-") as directory:
            if project.youtube_url and not project.source:
                source, metadata, title = download_youtube(project, directory)
                with source.open("rb") as file:
                    name = project.source.storage.save(
                        f"media/clips/{project.pk}/{token}-source.mp4", File(file)
                    )
                if not update_jobs(
                    rows.filter(status=ClipProjectStatus.DOWNLOADING),
                    source=name,
                    duration=metadata["duration"],
                    width=metadata["width"],
                    height=metadata["height"],
                    title=title if project.title == "YouTube video" else project.title,
                    status=ClipProjectStatus.TRANSCRIBING,
                    updated_at=timezone.now(),
                ):
                    project.source.storage.delete(name)
                    return
                project.refresh_from_db()
            try:
                validate_range(
                    project.range_start,
                    project.range_end,
                    project.min_duration,
                    project.duration,
                )
            except ValidationError as exc:
                raise SourceImportError(
                    " ".join(str(detail) for detail in exc.detail)
                ) from exc
            if not project.source_key:
                key = source_key(project)
                if not update_jobs(
                    rows.filter(status=ClipProjectStatus.TRANSCRIBING), source_key=key
                ):
                    return
                project.source_key = key
            if not project.preview:
                preview = make_preview(project, directory)
                metadata = video_metadata(preview)
                with preview.open("rb") as file:
                    name = project.preview.storage.save(
                        f"media/clips/{project.pk}/{token}-preview.mp4", File(file)
                    )
                if not update_jobs(
                    rows.filter(status=ClipProjectStatus.TRANSCRIBING),
                    preview=name,
                    width=metadata["width"],
                    height=metadata["height"],
                    updated_at=timezone.now(),
                ):
                    project.preview.storage.delete(name)
                    return
                project.refresh_from_db()
            if not project.words:
                words = reuse_transcript(project)
                if words is None:
                    words = transcribe_source(project, rows, directory)
                if words is None:
                    return
                if not words:
                    raise ValueError("No speech")
                if not update_jobs(
                    rows.filter(status=ClipProjectStatus.TRANSCRIBING),
                    words=words,
                    updated_at=timezone.now(),
                ):
                    return
                project.words = words
            if not update_jobs(
                rows.filter(status=ClipProjectStatus.TRANSCRIBING),
                status=ClipProjectStatus.ANALYZING,
                updated_at=timezone.now(),
            ):
                return
            candidates = suggest_clips(
                project,
                is_current=lambda: rows.filter(
                    status=ClipProjectStatus.ANALYZING
                ).exists(),
            )
            with transaction.atomic():
                current = (
                    rows.select_for_update()
                    .filter(status=ClipProjectStatus.ANALYZING)
                    .first()
                )
                if current is None:
                    return
                existing = list(current.clips.values("start", "end"))
                for candidate in candidates:
                    if len(existing) >= MAX_CLIPS_PER_PROJECT:
                        break
                    if any(overlapping(candidate, other) for other in existing):
                        continue
                    Clip.objects.create(
                        project=current,
                        **candidate,
                        words=clip_words(
                            project.words, candidate["start"], candidate["end"]
                        ),
                        style=dict(PROJECT_STYLE_DEFAULTS),
                    )
                    existing.append(candidate)
                update_jobs(
                    rows,
                    status=ClipProjectStatus.READY,
                    error="",
                    updated_at=timezone.now(),
                )
    except Exception as exc:
        logger.exception("Clip project processing failed for %s", project_id)
        update_jobs(
            rows.filter(
                status__in=[
                    ClipProjectStatus.DOWNLOADING,
                    ClipProjectStatus.TRANSCRIBING,
                    ClipProjectStatus.ANALYZING,
                ]
            ),
            status=ClipProjectStatus.FAILED,
            error=str(exc)
            if isinstance(exc, SourceImportError)
            else "Could not import this YouTube video. Check that it is publicly available, or upload a file instead."
            if project.youtube_url and not project.source
            else "Could not finish finding clips. Check your provider keys and retry. Saved transcription will be reused; you can also add clips manually.",
            updated_at=timezone.now(),
        )
