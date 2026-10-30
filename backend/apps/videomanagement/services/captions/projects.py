"""Timestamped captions over an uploaded video's original picture and sound."""

import logging
import tempfile
from pathlib import Path

from django.core.files import File
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import APIException, ValidationError

from apps.common.media import run_ffmpeg
from apps.videomanagement import tasks
from apps.videomanagement.models import CaptionProject, CaptionProjectStatus
from apps.videomanagement.services.captions.transcription import transcribe_audio
from apps.videomanagement.utils.captions.cues import word_cues
from apps.videomanagement.utils.captions.styles import (
    PROJECT_STYLE_DEFAULTS,
    project_caption_style,
)
from apps.videomanagement.utils.captions.timing import validate_word_bounds
from apps.videomanagement.utils.composer.captions import write_ass
from apps.videomanagement.utils.fonts import subtitles_filter
from apps.videomanagement.utils.timing import video_metadata

logger = logging.getLogger(__name__)

BUSY_STATUSES = {
    CaptionProjectStatus.QUEUED,
    CaptionProjectStatus.TRANSCRIBING,
    CaptionProjectStatus.RENDER_QUEUED,
    CaptionProjectStatus.RENDERING,
}


class CaptionConflict(APIException):
    status_code = 409
    default_detail = "Wait for caption processing to finish before making changes."


def queue_caption_job(project, *, render=False):
    with transaction.atomic():
        locked = CaptionProject.objects.select_for_update().get(pk=project.pk)
        # A newly uploaded project has no job yet. Jobs older than 30 minutes can be retried.
        if (
            locked.status in BUSY_STATUSES
            and locked.job_id
            and (timezone.now() - locked.updated_at).total_seconds() < 1800
        ):
            raise CaptionConflict()
        if not render and locked.words:
            raise CaptionConflict(
                "This project already has captions. Edit them in the word list."
            )
        if render and not locked.words:
            raise CaptionConflict("Add some caption words before exporting.")
        status = (
            CaptionProjectStatus.RENDER_QUEUED
            if render
            else CaptionProjectStatus.QUEUED
        )
        locked.mark_queued(status)
        token = locked.job_id
    try:
        tasks.caption_project_task.apply_async(
            args=(str(project.pk), str(token), render)
        )
    except Exception as exc:
        CaptionProject.objects.filter(pk=project.pk, job_id=token).update(
            status=CaptionProjectStatus.READY
            if locked.words
            else CaptionProjectStatus.FAILED,
            error="Could not queue processing. Please retry.",
            updated_at=timezone.now(),
        )
        error = APIException(
            "Project saved, but processing could not be queued. Please retry."
        )
        error.status_code = 503
        raise error from exc
    project.refresh_from_db()
    return project


def transcribe_project(project, directory):
    preview = Path(directory, "preview.mp4")
    run_ffmpeg(
        [
            "-i",
            project.source.path,
            "-map",
            "0:v:0",
            "-map",
            "0:a:0",
            "-vf",
            "scale=trunc(iw/2)*2:trunc(ih/2)*2",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            str(preview),
        ],
        timeout=1100,
    )
    words = transcribe_audio(
        project.source.path, project.created_by, project.duration, directory
    )
    if not words:
        raise ValueError(
            "No speech was detected. Try a video with clearer spoken audio."
        )
    return words, preview


def project_cues(project, *, highlight=False):
    return word_cues(project.words, project_caption_style(project), highlight=highlight)


def write_project_ass(project, path):
    write_ass(
        path,
        project_cues(project, highlight=True),
        (project.width, project.height),
        project_caption_style(project),
    )


def process_caption_project(project_id, token, render=False):
    queued, running = (
        (CaptionProjectStatus.RENDER_QUEUED, CaptionProjectStatus.RENDERING)
        if render
        else (CaptionProjectStatus.QUEUED, CaptionProjectStatus.TRANSCRIBING)
    )
    rows = CaptionProject.objects.filter(pk=project_id, job_id=token)
    if not rows.filter(status=queued).update(status=running, updated_at=timezone.now()):
        return
    project = rows.select_related("created_by").get()
    try:
        if not project.created_by.is_active:
            raise ValueError("Account is inactive.")
        with tempfile.TemporaryDirectory(prefix="captions-") as directory:
            if render:
                write_project_ass(project, Path(directory, "captions.ass"))
                output = Path(directory, "captioned.mp4")
                run_ffmpeg(
                    [
                        "-i",
                        project.source.path,
                        "-map",
                        "0:v:0",
                        "-map",
                        "0:a:0",
                        "-vf",
                        "scale=trunc(iw/2)*2:trunc(ih/2)*2,"
                        + subtitles_filter("captions.ass", directory),
                        "-c:v",
                        "libx264",
                        "-preset",
                        "fast",
                        "-crf",
                        "20",
                        "-pix_fmt",
                        "yuv420p",
                        "-c:a",
                        "aac",
                        "-movflags",
                        "+faststart",
                        str(output),
                    ],
                    cwd=directory,
                    timeout=1100,
                )
                with output.open("rb") as file:
                    name = project.output.storage.save(
                        f"media/captions/{project.pk}/{token}.mp4", File(file)
                    )
                updates = {"status": CaptionProjectStatus.COMPLETED, "output": name}
            else:
                words, preview = transcribe_project(project, directory)
                metadata = video_metadata(preview)
                with preview.open("rb") as file:
                    name = project.preview.storage.save(
                        f"media/captions/{project.pk}/{token}-preview.mp4", File(file)
                    )
                updates = {
                    "status": CaptionProjectStatus.READY,
                    "words": words,
                    "preview": name,
                    "width": metadata["width"],
                    "height": metadata["height"],
                }
            field = project.output if render else project.preview
            with transaction.atomic():
                current = rows.select_for_update().filter(status=running).first()
                if current:
                    previous_name = (
                        current.output.name if render else current.preview.name
                    )
                    rows.filter(status=running).update(
                        **updates, error="", updated_at=timezone.now()
                    )
                    if previous_name and previous_name != name:
                        transaction.on_commit(
                            lambda: field.storage.delete(previous_name), robust=True
                        )
                else:
                    field.storage.delete(name)
    except Exception as exc:
        logger.exception("Caption processing failed for %s", project_id)
        message = (
            str(exc)
            if isinstance(exc, ValueError)
            else "Could not export the video. Please retry."
            if render
            else "Could not finish processing. Check your OpenAI key or try again."
        )
        rows.filter(status=running).update(
            status=CaptionProjectStatus.READY
            if project.words
            else CaptionProjectStatus.FAILED,
            error=message[:300],
            updated_at=timezone.now(),
        )


def create_caption_project(user, source, metadata, title=""):
    project = CaptionProject.objects.create(
        created_by=user,
        source=source,
        title=title or Path(source.name).stem[:100],
        duration=metadata["duration"],
        width=metadata["width"],
        height=metadata["height"],
        style=dict(PROJECT_STYLE_DEFAULTS),
    )
    try:
        queue_caption_job(project)
    except APIException as exc:
        # Retain the upload so a failed dispatch can be retried without uploading again.
        project.refresh_from_db()
        if exc.status_code != 503 or project.status != CaptionProjectStatus.FAILED:
            raise
    return project


def update_caption_project(project, **changes):
    changes = dict(changes)
    with transaction.atomic():
        project = CaptionProject.objects.select_for_update().get(pk=project.pk)
        if project.status in BUSY_STATUSES:
            raise CaptionConflict()
        if "revision" not in changes:
            raise ValidationError({"revision": "Reload this project before saving."})
        if changes.pop("revision") != project.updated_at:
            raise CaptionConflict(
                "This project changed in another editor. Reload it before saving; your changes are still here."
            )
        if "words" in changes:
            validate_word_bounds(changes["words"], project.duration)
        for key, value in changes.items():
            setattr(
                project, key, {**project.style, **value} if key == "style" else value
            )
        if {"words", "style"} & changes.keys():
            old_output = project.output.name
            project.output = ""
            project.status = (
                CaptionProjectStatus.READY
                if project.words
                else CaptionProjectStatus.FAILED
            )
            if old_output:
                transaction.on_commit(
                    lambda: project.output.storage.delete(old_output), robust=True
                )
        project.error = ""
        project.save()
    return project
