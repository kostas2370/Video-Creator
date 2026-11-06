from uuid import uuid4

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError

from apps.videomanagement import tasks
from apps.videomanagement.events import publish_update
from apps.videomanagement.exceptions import (
    GenerationQueueUnavailable,
    VideoEditConflict,
)
from apps.videomanagement.models import Avatar, Intro, Outro, Video, VideoStatus
from apps.videomanagement.services.media.selection import available_voice, owned_asset
from apps.videomanagement.services.scenes.editing import changed, editable_video


def video_update(video: Video, **changes) -> Video:
    """Apply only supplied fields, resolving every asset before changing the video."""
    if {
        "generation_mode",
        "visual_continuity",
        "transition_default",
        "transition_duration",
        "intro_transition",
        "intro_transition_duration",
        "intro",
        "voice_id",
        "retry_narration",
        "avatar",
        "caption_style",
        "caption_config",
    } & changes.keys():
        with editable_video(video.pk) as locked_video:
            return _apply_video_changes(locked_video, changes)
    return _apply_video_changes(video, changes)


def _apply_video_changes(video, changes):
    retry_narration = changes.get("retry_narration", False)
    if retry_narration and not (
        video.status == VideoStatus.FAILED and video.narration_retry_status
    ):
        raise ValidationError(
            {"retry_narration": "There is no failed narration to retry."}
        )
    updates = {}
    for field, model in (("avatar", Avatar), ("intro", Intro), ("outro", Outro)):
        if field in changes:
            updates[field] = owned_asset(model, changes[field], video.created_by)

    if "title" in changes:
        updates["title"] = changes["title"]

    selected_avatar = updates.get("avatar")
    selected_voice = selected_avatar.voice if selected_avatar is not None else None
    if "voice_id" in changes:
        if updates.get("avatar", video.avatar_id):
            raise ValidationError({"voice_id": "The avatar uses its assigned voice."})
        selected_voice = available_voice(changes["voice_id"], video.created_by)
    voice_changed = (
        selected_voice is not None and video.voice_model_id != selected_voice.pk
    )
    if voice_changed:
        updates["voice_model"] = selected_voice

    settings_fields = (
        "generation_mode",
        "video_format",
        "platform",
        "subtitles",
        "caption_style",
        "caption_config",
        "avatar_position",
        "visual_continuity",
        "transition_default",
        "transition_duration",
        "intro_transition",
        "intro_transition_duration",
    )
    settings_changes = {
        field: changes[field] for field in settings_fields if field in changes
    }
    if settings_changes:
        updates["settings"] = {**(video.settings or {}), **settings_changes}

    for field, value in updates.items():
        setattr(video, field, value)
    video.save(update_fields=[*updates, "updated_at"])
    if (
        (voice_changed or retry_narration)
        and (video.settings or {}).get("narration", True)
        and video.scenes.exists()
    ):
        previous_status = video.narration_retry_status or video.status
        video.operation_id = uuid4()
        video.narration_retry_status = previous_status
        video.status = VideoStatus.GENERATION
        video.save(
            update_fields=[
                "status",
                "operation_id",
                "narration_retry_status",
                "updated_at",
            ]
        )
        try:
            # The worker locks this row before reading the committed settings.
            tasks.regenerate_narration_task.delay(
                str(video.pk), previous_status, operation_id=str(video.operation_id)
            )
        except Exception as exc:
            raise GenerationQueueUnavailable(
                "Could not queue narration. Your settings were not changed. Please try again."
            ) from exc
        video.narration_queued = True
        transaction.on_commit(
            lambda: publish_update(f"video.{video.pk}", video_id=video.pk)
        )
    return video


def update_music_settings(video, changes):
    with editable_video(video.pk) as video:
        video.settings = {**(video.settings or {}), **changes}
        video.save(update_fields=["settings"])
        changed(video)
    return video


def delete_video(video, *, draft_only=False):
    with transaction.atomic():
        locked = get_object_or_404(Video.objects.select_for_update(), pk=video.pk)
        if locked.status not in ("REVIEW", "READY", "COMPLETED", "FAILED"):
            raise VideoEditConflict(
                "This project is still processing. Wait for it to finish before deleting it."
            )
        if draft_only and not (
            locked.status == "REVIEW"
            or (locked.status == "FAILED" and not locked.scenes.exists())
        ):
            raise VideoEditConflict(
                "This project is no longer a draft. Open it or manage it from My videos."
            )
        locked.delete()
