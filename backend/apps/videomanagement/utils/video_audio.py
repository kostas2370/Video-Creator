"""Shared direction for generated sound and inclusion in the final edit."""


def audio_mode(choices):
    mode = choices.get("video_audio_mode", "AUTO")
    if mode == "AUTO":
        return "AMBIENT" if choices.get("narration", True) else "DIALOGUE"
    return mode


def audio_direction(mode):
    if mode == "SILENT":
        return (
            "Generate a silent clip: no speech, ambient sound, sound effects or music."
        )
    if mode == "DIALOGUE":
        return (
            "Allow brief, natural character dialogue with synchronized mouth movements "
            "when it serves the scene, plus natural ambient sound. Use explicitly supplied "
            "dialogue verbatim; otherwise characters may speak short lines consistent with "
            "the scene and the project's language. Do not add a voice-over narrator. "
            "No background music; the editor supplies the shared soundtrack."
        )
    return (
        "Use natural ambient sound and sound effects only. No character speech or "
        "voice-over narration. No background music; the editor supplies the shared soundtrack."
    )


def clip_audio_enabled(scene, image):
    return bool(
        image
        and image.with_audio
        and (scene.video.settings or {}).get("video_audio_enabled", True)
    )


def generated_audio_enabled(choices):
    return choices.get("video_audio_enabled", not choices.get("narration", True))
