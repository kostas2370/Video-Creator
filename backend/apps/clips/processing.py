import logging
import math
import tempfile
from pathlib import Path

from django.core.files import File
from django.db import transaction
from django.utils import timezone

from apps.videomanagement.services.captions.transcription import transcribe_audio
from apps.videomanagement.utils.captions.styles import PROJECT_STYLE_DEFAULTS
from apps.videomanagement.utils.timing import video_metadata

from .choices import ClipProjectStatus
from .constants import MAX_CLIPS_PER_PROJECT
from .highlights import overlapping, suggest_clips
from .media import run_ffmpeg
from .models import Clip, ClipProject
from .services import clip_words

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
    for index in range(len(parts), math.ceil(project.duration / CHUNK_SECONDS)):
        offset = index * CHUNK_SECONDS
        if not rows.filter(status=ClipProjectStatus.TRANSCRIBING).exists():
            return None
        start = max(0, offset - 2)
        end = min(project.duration, offset + CHUNK_SECONDS + 2)
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
                min(project.duration, word["end"] + start),
            )
            midpoint = (word_start + word_end) / 2
            if offset <= midpoint < min(project.duration, offset + CHUNK_SECONDS):
                adjusted.append(
                    {
                        "text": word["text"],
                        "start": round(word_start, 4),
                        "end": round(word_end, 4),
                    }
                )
        parts.append(adjusted)
        if not rows.filter(status=ClipProjectStatus.TRANSCRIBING).update(
            transcript_parts=parts, updated_at=timezone.now()
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
    if not rows.filter(status=ClipProjectStatus.QUEUED).update(
        status=ClipProjectStatus.TRANSCRIBING, updated_at=timezone.now()
    ):
        return
    project = rows.select_related("created_by").get()
    try:
        if not project.created_by.is_active:
            raise ValueError("Inactive account")
        with tempfile.TemporaryDirectory(prefix="clips-") as directory:
            if not project.preview:
                preview = make_preview(project, directory)
                metadata = video_metadata(preview)
                with preview.open("rb") as file:
                    name = project.preview.storage.save(
                        f"media/clips/{project.pk}/{token}-preview.mp4", File(file)
                    )
                if not rows.filter(status=ClipProjectStatus.TRANSCRIBING).update(
                    preview=name,
                    width=metadata["width"],
                    height=metadata["height"],
                    updated_at=timezone.now(),
                ):
                    project.preview.storage.delete(name)
                    return
                project.refresh_from_db()
            if not project.words:
                words = transcribe_source(project, rows, directory)
                if words is None:
                    return
                if not words:
                    raise ValueError("No speech")
                if not rows.filter(status=ClipProjectStatus.TRANSCRIBING).update(
                    words=words, updated_at=timezone.now()
                ):
                    return
                project.words = words
            if not rows.filter(status=ClipProjectStatus.TRANSCRIBING).update(
                status=ClipProjectStatus.ANALYZING, updated_at=timezone.now()
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
                rows.update(
                    status=ClipProjectStatus.READY, error="", updated_at=timezone.now()
                )
    except Exception:
        logger.exception("Clip project processing failed for %s", project_id)
        rows.filter(
            status__in=[ClipProjectStatus.TRANSCRIBING, ClipProjectStatus.ANALYZING]
        ).update(
            status=ClipProjectStatus.FAILED,
            error="Could not finish finding clips. Check your provider keys and retry. Saved transcription will be reused; you can also add clips manually.",
            updated_at=timezone.now(),
        )
