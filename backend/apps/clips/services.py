import logging
from pathlib import Path

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404

from apps.videomanagement.events import publish_update
from apps.videomanagement.utils.captions.styles import PROJECT_STYLE_DEFAULTS
from apps.videomanagement.utils.captions.timing import validate_word_bounds

from .choices import CLIP_BUSY, PROJECT_BUSY, ClipProjectStatus, ClipStatus
from .constants import (
    CLIP_RENDER_FIELDS,
    EXPORT_STALE_AFTER,
    MAX_CLIPS_PER_PROJECT,
    PROJECT_STALE_AFTER,
)
from .events import update_jobs
from .exceptions import ClipConflict, ClipQueueUnavailable
from .models import Clip, ClipProject

logger = logging.getLogger(__name__)


def clip_words(words, start, end):
    return [
        {
            "text": word["text"],
            "start": round(max(start, word["start"]) - start, 4),
            "end": min(end - start, round(min(end, word["end"]) - start, 4)),
        }
        for word in words
        if word["end"] > start and word["start"] < end
    ]


def project_editable(project):
    if project.status in PROJECT_BUSY:
        raise ClipConflict(
            "Wait for highlight processing to finish before editing clips."
        )


def create_project(user, source=None, metadata=None, **options):
    options["title"] = options.get("title") or (
        Path(source.name).stem[:100] if source else "YouTube video"
    )
    metadata = metadata or {"duration": 0, "width": 0, "height": 0}
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
    except ClipQueueUnavailable:
        project.refresh_from_db()
    return project


def queue_project(project):
    # Tasks import processing, which imports this service module.
    from .tasks import process_project_task

    with transaction.atomic():
        project = get_object_or_404(
            ClipProject.objects.select_for_update(), pk=project.pk
        )
        if project.status == ClipProjectStatus.READY:
            raise ClipConflict(
                "Highlights are already prepared. Add or edit clips in the workspace."
            )
        if (
            project.status in PROJECT_BUSY
            and project.job_id
            and project.updated_at > timezone.now() - PROJECT_STALE_AFTER
        ):
            raise ClipConflict("Highlight processing is already running.")
        project.mark_queued(ClipProjectStatus.QUEUED)
        publish_update(f"clips.{project.pk}", kind="clips")
    try:
        process_project_task.apply_async(args=(str(project.pk), str(project.job_id)))
    except Exception as exc:
        update_jobs(
            ClipProject.objects.filter(
                pk=project.pk, job_id=project.job_id, status=ClipProjectStatus.QUEUED
            ),
            status=ClipProjectStatus.FAILED,
            error="Could not queue processing. Retry without uploading again.",
        )
        raise ClipQueueUnavailable() from exc
    project.refresh_from_db()
    return project


def save_clip(project, changes, clip_id=None):
    with transaction.atomic():
        project = get_object_or_404(
            ClipProject.objects.select_for_update(), pk=project.pk
        )
        project_editable(project)
        if clip_id:
            clip = get_object_or_404(project.clips.select_for_update(), pk=clip_id)
            if clip.status in CLIP_BUSY:
                raise ClipConflict(
                    "Wait for this clip's export to finish before editing."
                )
            if changes.pop("revision", None) != clip.updated_at:
                raise ClipConflict()
        else:
            if project.clips.count() >= MAX_CLIPS_PER_PROJECT:
                raise ValidationError("Keep up to 20 clips per project.")
            changes.pop("revision", None)
            clip = Clip(
                project=project,
                start=changes["start"],
                end=changes["end"],
                style=dict(PROJECT_STYLE_DEFAULTS),
            )
        original = {field: getattr(clip, field) for field in CLIP_RENDER_FIELDS}
        bounds_changed = clip_id is None or any(
            key in changes and changes[key] != getattr(clip, key)
            for key in ("start", "end")
        )
        for key, value in changes.items():
            setattr(clip, key, {**clip.style, **value} if key == "style" else value)
        if bounds_changed and "words" not in changes:
            clip.words = clip_words(project.words, clip.start, clip.end)
        validate_word_bounds(clip.words, clip.end - clip.start)
        render_changed = clip_id is None or any(
            getattr(clip, field) != original[field] for field in CLIP_RENDER_FIELDS
        )
        previous_output = clip.output.name if render_changed else ""
        if render_changed:
            clip.output, clip.error, clip.status = "", "", ClipStatus.READY
        clip.save()
        publish_update(f"clips.{project.pk}", kind="clips")
        if previous_output:
            transaction.on_commit(
                lambda: clip.output.storage.delete(previous_output), robust=True
            )
    return clip


def queue_exports(project, clip_ids):
    # Tasks import processing, which imports this service module.
    from .tasks import export_clip_task

    if not clip_ids or len(clip_ids) != len(set(clip_ids)):
        raise ValidationError("Select distinct clips to export.")
    with transaction.atomic():
        project = get_object_or_404(
            ClipProject.objects.select_for_update(), pk=project.pk
        )
        project_editable(project)
        clips = list(project.clips.select_for_update().filter(pk__in=clip_ids))
        if len(clips) != len(clip_ids):
            raise ValidationError("Choose clips from this project.")
        for clip in clips:
            if (
                clip.status in CLIP_BUSY
                and clip.updated_at > timezone.now() - EXPORT_STALE_AFTER
            ):
                raise ClipConflict("One of these clips is already exporting.")
        for clip in clips:
            clip.mark_queued(ClipStatus.QUEUED)
        publish_update(f"clips.{project.pk}", kind="clips")
    for clip in clips:
        try:
            export_clip_task.apply_async(args=(str(clip.pk), str(clip.job_id)))
        except Exception:
            logger.exception("Could not queue clip export %s", clip.pk)
            update_jobs(
                Clip.objects.filter(
                    pk=clip.pk, job_id=clip.job_id, status=ClipStatus.QUEUED
                ),
                status=ClipStatus.FAILED,
                error="Could not queue export. Please retry.",
            )
        clip.refresh_from_db()
    return clips


def delete_project(project):
    with transaction.atomic():
        project = get_object_or_404(
            ClipProject.objects.select_for_update(), pk=project.pk
        )
        fresh = timezone.now() - EXPORT_STALE_AFTER
        if (
            project.status in PROJECT_BUSY
            and project.updated_at > timezone.now() - PROJECT_STALE_AFTER
            or project.clips.filter(status__in=CLIP_BUSY, updated_at__gt=fresh).exists()
        ):
            raise ClipConflict(
                "Wait for processing to finish before deleting this project."
            )
        project_id = project.pk
        project.delete()
        publish_update(f"clips.{project_id}", kind="clips")


def delete_clip(project, clip_id):
    with transaction.atomic():
        project = get_object_or_404(
            ClipProject.objects.select_for_update(), pk=project.pk
        )
        project_editable(project)
        clip = get_object_or_404(project.clips.select_for_update(), pk=clip_id)
        if clip.status in CLIP_BUSY:
            raise ClipConflict(
                "Wait for this clip's export to finish before removing it."
            )
        clip.delete()
        publish_update(f"clips.{project.pk}", kind="clips")


def reap_stalled_exports(project_id=None):
    rows = Clip.objects.filter(
        status__in=CLIP_BUSY, updated_at__lte=timezone.now() - EXPORT_STALE_AFTER
    )
    if project_id is not None:
        rows = rows.filter(project_id=project_id)
    return update_jobs(
        rows,
        status=ClipStatus.FAILED,
        error="Export stopped responding. Retry this clip; your edits are saved.",
    )
