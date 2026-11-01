from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError

from apps.videomanagement.exceptions import VideoEditConflict

from apps.videomanagement.models import Avatar, Intro, Outro, Video
from apps.videomanagement.services.media.selection import available_voice, owned_asset
from apps.videomanagement.services.scenes.editing import changed, editable_video
from apps.videomanagement.services.scenes.narration import update_scene


def video_update(video: Video, **changes) -> Video:
    """Apply only supplied fields, resolving every asset before changing the video."""
    if {
        "visual_continuity",
        "transition_default",
        "transition_duration",
        "intro_transition",
        "intro_transition_duration",
        "intro",
        "voice_id",
        "caption_style",
        "caption_config",
    } & changes.keys():
        with editable_video(video.pk) as locked_video:
            return _apply_video_changes(locked_video, changes)
    return _apply_video_changes(video, changes)


def _apply_video_changes(video, changes):
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
    if voice_changed and (video.settings or {}).get("narration", True):
        for scene in video.scenes.all():
            update_scene(scene)
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
