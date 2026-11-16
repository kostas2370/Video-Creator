"""Compare render inputs, excluding project notes and publishing metadata."""

import hashlib
import json

from django.core.exceptions import SuspiciousFileOperation

from apps.videomanagement.export_settings import export_settings
from apps.videomanagement.utils.audio_editing import narration_enabled, narration_file
from apps.videomanagement.utils.captions.styles import video_caption_style
from apps.videomanagement.utils.composer.scene_cache import file_identity
from apps.videomanagement.utils.transitions import default_transition
from apps.videomanagement.video_formats import output_size

SCENE_FIELDS = (
    "text",
    "caption_alignment",
    "overlays",
    "audio_settings",
    "motion_style",
    "animation_preset",
    "animation_accents",
    "motion_intensity",
    "pause_after",
    "cuts",
    "transition_after",
    "transition_duration",
    "is_last",
)
RENDER_SETTINGS = (
    "narration",
    "subtitles",
    "avatar_position",
    "loop_visual",
    "video_audio_enabled",
    "transition_duration",
    "intro_transition",
    "intro_transition_duration",
    "music_volume",
    "music_ducking",
    "music_fade_in",
    "music_fade_out",
    "duck_level",
    "duck_attack",
    "duck_release",
)


def render_settings(video):
    choices = video.settings or {}
    return {
        **{key: choices[key] for key in RENDER_SETTINGS if key in choices},
        "size": output_size(choices.get("video_format")),
        "export": export_settings(choices),
        "transition_default": default_transition(choices),
        "captions": video_caption_style(video).to_dict()
        if choices.get("subtitles")
        else None,
    }


def scene_visual(scene):
    image = next(iter(scene.scene_images.all()), None)
    return (
        {"file": media_identity(image.file), "with_audio": image.with_audio}
        if image
        else None
    )


def media_identity(file):
    if not file:
        return None
    try:
        return file_identity(file.path)
    except (ValueError, NotImplementedError, SuspiciousFileOperation):
        return str(file)


def export_source_key(video, *, scenes=None):
    rows = video.scenes.all() if scenes is None else scenes
    value = {
        "settings": render_settings(video),
        "video_type": video.video_type,
        "cuts": video.cuts,
        "music": media_identity(video.music.file) if video.music_id else None,
        "intro": media_identity(video.intro.file) if video.intro_id else None,
        "outro": media_identity(video.outro.file) if video.outro_id else None,
        "avatar": str(video.avatar_id or ""),
        "scenes": [
            {
                "id": str(scene.pk),
                **{key: getattr(scene, key) for key in SCENE_FIELDS},
                "narration": media_identity(narration_file(scene))
                if narration_enabled(scene)
                else None,
                "logo": media_identity(scene.overlay_logo),
                "visual": scene_visual(scene),
            }
            for scene in rows
        ],
    }
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, default=str).encode()
    ).hexdigest()


def export_freshness(video):
    if not video.output:
        return {"status": "none", "exported_at": None}
    status = "unknown"
    if video.export_source_key:
        status = (
            "current"
            if video.export_source_key == export_source_key(video)
            else "stale"
        )
    return {"status": status, "exported_at": video.exported_at}
