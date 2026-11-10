"""Shared direction for generated sound and inclusion in the final edit."""


def audio_mode(choices):
    mode = choices.get("video_audio_mode", "AUTO")
    if mode == "AUTO":
        return "AMBIENT" if choices.get("narration", True) else "DIALOGUE"
    return mode


def clip_audio_enabled(scene, image):
    return bool(
        image
        and image.with_audio
        and (scene.video.settings or {}).get("video_audio_enabled", True)
    )
