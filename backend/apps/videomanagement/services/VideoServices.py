from .asset_selection import owned_asset
from ..models import Avatar, Intro, Outro, Video
from ..utils.audio_utils import update_scene


def video_update(video: Video, **changes) -> Video:
    """Apply only supplied fields, resolving every asset before changing the video."""
    updates = {}
    for field, model in (("avatar", Avatar), ("intro", Intro), ("outro", Outro)):
        if field in changes:
            updates[field] = owned_asset(model, changes[field], video.created_by)

    if "title" in changes:
        updates["title"] = changes["title"]

    selected_avatar = updates.get("avatar")
    voice_changed = (
        selected_avatar is not None and video.voice_model_id != selected_avatar.voice_id
    )
    if voice_changed:
        updates["voice_model"] = selected_avatar.voice

    settings_fields = ("video_format", "platform", "subtitles", "avatar_position", "transition_default", "transition_duration")
    settings_changes = {
        field: changes[field] for field in settings_fields if field in changes
    }
    if settings_changes:
        updates["settings"] = {**(video.settings or {}), **settings_changes}

    for field, value in updates.items():
        setattr(video, field, value)
    video.save(update_fields=[*updates, "updated_at"])
    if voice_changed:
        for scene in video.scenes.all():
            update_scene(scene)
    return video
