"""Resolve scene transition defaults without loading the rendering runtime."""

from ..models import TransitionStyle


def default_transition(settings):
    fallback = (
        TransitionStyle.CUT
        if settings.get("creation_mode") == "SERIES"
        else TransitionStyle.FADE
    )
    return settings.get("transition_default", fallback)


def scene_transition(scene, settings):
    style = scene.transition_after
    if style == TransitionStyle.DEFAULT:
        style = default_transition(settings)
    duration = scene.transition_duration
    if duration is None:
        duration = settings.get("transition_duration")
    return style, duration


def intro_transition(settings):
    style = settings.get("intro_transition", TransitionStyle.DEFAULT)
    if style == TransitionStyle.DEFAULT:
        style = default_transition(settings)
    duration = settings.get("intro_transition_duration")
    if duration is None:
        duration = settings.get("transition_duration")
    return style, duration
