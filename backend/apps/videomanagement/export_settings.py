EXPORT_PRESETS = {
    "DRAFT": {"crf": 28, "preset": "veryfast"},
    "STANDARD": {"crf": 23, "preset": "fast"},
    "HIGH": {"crf": 18, "preset": "slow"},
}
DEFAULT_EXPORT_PRESET = "STANDARD"
EXPORT_FRAME_RATES = (24, 30)
DEFAULT_EXPORT_FPS = 24


def export_settings(settings):
    preset = settings.get("export_preset")
    if not isinstance(preset, str) or preset not in EXPORT_PRESETS:
        preset = DEFAULT_EXPORT_PRESET
    fps = settings.get("export_fps")
    if type(fps) is not int or fps not in EXPORT_FRAME_RATES:
        fps = DEFAULT_EXPORT_FPS
    return {**EXPORT_PRESETS[preset], "fps": fps}
