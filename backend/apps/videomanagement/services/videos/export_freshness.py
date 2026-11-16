"""Compare render inputs, excluding project notes and publishing metadata."""

import hashlib
import json

from django.core.exceptions import SuspiciousFileOperation

from apps.videomanagement.utils.composer.scene_cache import file_identity


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
    "shot_plan",
)
# These guide future generation and do not alter saved media playback.
GENERATION_SETTINGS = {
    "narration_language",
    "gpt_model",
    "generation_mode",
    "creation_mode",
    "character_profiles",
    "reference_images",
    "visual_continuity",
}


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
        "settings": {
            key: value
            for key, value in (video.settings or {}).items()
            if key not in GENERATION_SETTINGS
        },
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
                "speech": media_identity(scene.file),
                "voiceover": media_identity(scene.voiceover),
                "logo": media_identity(scene.overlay_logo),
                "visuals": [
                    {"file": media_identity(image.file), "with_audio": image.with_audio}
                    for image in scene.scene_images.all()
                ],
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
