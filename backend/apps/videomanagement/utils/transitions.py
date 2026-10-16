"""Resolve scene transition defaults without loading the rendering runtime."""

from ..models import TransitionStyle


def scene_transition(scene, settings):
    style = scene.transition_after
    if style == TransitionStyle.DEFAULT:
        style = settings.get("transition_default", TransitionStyle.FADE)
    duration = scene.transition_duration
    if duration is None:
        duration = settings.get("transition_duration")
    return style, duration


def intro_transition(settings):
    style = settings.get("intro_transition", TransitionStyle.DEFAULT)
    if style == TransitionStyle.DEFAULT:
        style = settings.get("transition_default", TransitionStyle.FADE)
    duration = settings.get("intro_transition_duration")
    if duration is None:
        duration = settings.get("transition_duration")
    return style, duration
