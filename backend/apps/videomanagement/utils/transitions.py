"""Resolve scene transition defaults without loading the rendering runtime."""


def scene_transition(scene, settings):
    style = scene.transition_after
    if style == "DEFAULT":
        style = settings.get("transition_default", "FADE")
    duration = scene.transition_duration
    if duration is None:
        duration = settings.get("transition_duration")
    return style, duration
