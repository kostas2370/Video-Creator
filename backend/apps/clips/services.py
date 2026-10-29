import logging
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import APIException, ValidationError

from apps.videomanagement.utils.captions.styles import PROJECT_STYLE_DEFAULTS
from apps.videomanagement.utils.captions.timing import validate_word_bounds

from .models import Clip, ClipProject

logger = logging.getLogger(__name__)
PROJECT_BUSY = {"QUEUED", "TRANSCRIBING", "ANALYZING"}
CLIP_BUSY = {"QUEUED", "RENDERING"}
STALE_AFTER = timedelta(hours=3)


class ClipConflict(APIException):
    status_code = 409
    default_detail = "This project changed. Reload it before continuing."


def clip_words(words, start, end):
    return [
        {
            "text": word["text"],
            "start": round(max(start, word["start"]) - start, 4),
            "end": round(min(end, word["end"]) - start, 4),
        }
        for word in words
        if word["end"] > start and word["start"] < end
    ]


def project_editable(project):
    if project.status in PROJECT_BUSY:
        raise ClipConflict(
            "Wait for highlight processing to finish before editing clips."
        )


def create_project(user, source, metadata, **options):
    options["title"] = options.get("title") or Path(source.name).stem[:100]
    project = ClipProject.objects.create(
        created_by=user,
        source=source,
        duration=metadata["duration"],
        width=metadata["width"],
        height=metadata["height"],
        **options,
    )
    try:
        queue_project(project)
    except APIException as exc:
        if exc.status_code != 503:
            raise
        project.refresh_from_db()
    return project


def queue_project(project):
    from .tasks import process_project_task

    with transaction.atomic():
        project = ClipProject.objects.select_for_update().get(pk=project.pk)
        if project.status == "READY":
            raise ClipConflict(
                "Highlights are already prepared. Add or edit clips in the workspace."
            )
        if (
            project.status in PROJECT_BUSY
            and project.job_id
            and project.updated_at > timezone.now() - STALE_AFTER
        ):
            raise ClipConflict("Highlight processing is already running.")
        project.job_id, project.status, project.error = uuid4(), "QUEUED", ""
        project.save(update_fields=["job_id", "status", "error", "updated_at"])
    try:
        process_project_task.apply_async(args=(str(project.pk), str(project.job_id)))
    except Exception as exc:
        ClipProject.objects.filter(
            pk=project.pk, job_id=project.job_id, status="QUEUED"
        ).update(
            status="FAILED",
            error="Could not queue processing. Retry without uploading again.",
            updated_at=timezone.now(),
        )
        error = APIException(
            "Upload saved, but processing could not be queued. Please retry."
        )
        error.status_code = 503
        raise error from exc
    project.refresh_from_db()
    return project


def save_clip(project, changes, clip_id=None):
    with transaction.atomic():
        project = ClipProject.objects.select_for_update().get(pk=project.pk)
        project_editable(project)
        if clip_id:
            clip = project.clips.select_for_update().get(pk=clip_id)
            if clip.status in CLIP_BUSY:
                raise ClipConflict(
                    "Wait for this clip's export to finish before editing."
                )
            if changes.pop("revision", None) != clip.updated_at:
                raise ClipConflict()
        else:
            if project.clips.count() >= 20:
                raise ValidationError("Keep up to 20 clips per project.")
            changes.pop("revision", None)
            clip = Clip(
                project=project,
                start=changes["start"],
                end=changes["end"],
                style=dict(PROJECT_STYLE_DEFAULTS),
            )
        bounds_changed = clip_id is None or any(
            key in changes and changes[key] != getattr(clip, key)
            for key in ("start", "end")
        )
        for key, value in changes.items():
            setattr(clip, key, {**clip.style, **value} if key == "style" else value)
        if bounds_changed and "words" not in changes:
            clip.words = clip_words(project.words, clip.start, clip.end)
        validate_word_bounds(clip.words, clip.end - clip.start)
        previous_output = clip.output.name
        clip.output, clip.error, clip.status = "", "", "READY"
        clip.save()
        if previous_output:
            transaction.on_commit(
                lambda: clip.output.storage.delete(previous_output), robust=True
            )
    return clip


def queue_exports(project, clip_ids):
    from .tasks import export_clip_task

    if not clip_ids or len(clip_ids) != len(set(clip_ids)):
        raise ValidationError("Select distinct clips to export.")
    with transaction.atomic():
        project = ClipProject.objects.select_for_update().get(pk=project.pk)
        project_editable(project)
        clips = list(project.clips.select_for_update().filter(pk__in=clip_ids))
        if len(clips) != len(clip_ids):
            raise ValidationError("Choose clips from this project.")
        for clip in clips:
            if (
                clip.status in CLIP_BUSY
                and clip.updated_at > timezone.now() - STALE_AFTER
            ):
                raise ClipConflict("One of these clips is already exporting.")
        for clip in clips:
            clip.job_id, clip.status, clip.error = uuid4(), "QUEUED", ""
            clip.save(update_fields=["job_id", "status", "error", "updated_at"])
    for clip in clips:
        try:
            export_clip_task.apply_async(args=(str(clip.pk), str(clip.job_id)))
        except Exception:
            logger.exception("Could not queue clip export %s", clip.pk)
            Clip.objects.filter(pk=clip.pk, job_id=clip.job_id, status="QUEUED").update(
                status="FAILED",
                error="Could not queue export. Please retry.",
                updated_at=timezone.now(),
            )
        clip.refresh_from_db()
    return clips
