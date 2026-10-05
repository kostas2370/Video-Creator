from .asset_selection import owned_asset
from ..models import Avatar, Intro, Outro, Video, VideoType
from ..utils.audio_utils import update_scene


def video_update(video: Video, **changes) -> Video:
    """Apply only supplied fields, resolving every asset before changing the video."""
    selected_assets = {}
    for field, model in (("avatar", Avatar), ("intro", Intro), ("outro", Outro)):
        if field in changes:
            selected_assets[field] = (
                None
                if field == "avatar" and video.video_type == VideoType.TWITCH
                else owned_asset(model, changes[field], video.created_by)
            )

    if "title" in changes:
        video.title = changes["title"]
    update_fields = list(selected_assets)
    if "title" in changes:
        update_fields.append("title")
    for field, asset in selected_assets.items():
        setattr(video, field, asset)

    selected_avatar = selected_assets.get("avatar")
    voice_changed = (
        selected_avatar is not None and video.voice_model_id != selected_avatar.voice_id
    )
    if voice_changed:
        video.voice_model = selected_avatar.voice
        update_fields.append("voice_model")

    settings_changes = {
        field: changes[field]
        for field in ("video_format", "platform")
        if field in changes
    }
    if video.video_type != VideoType.TWITCH:
        settings_changes.update({
            field: changes[field]
            for field in ("subtitles", "avatar_position")
            if field in changes
        })
    if settings_changes:
        video.settings = {**(video.settings or {}), **settings_changes}
        update_fields.append("settings")

    video.save(update_fields=[*update_fields, "updated_at"])
    if voice_changed:
        for scene in video.scenes.all():
            update_scene(scene)
    return video
