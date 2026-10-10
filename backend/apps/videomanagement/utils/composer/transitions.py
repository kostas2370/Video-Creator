from moviepy.editor import CompositeVideoClip, ImageClip, concatenate_videoclips

from ..transitions import scene_transition  # Re-export for existing composer callers.


def apply_fades(clip, *, fade_in=True, fade_out=True, fade_in_duration=None, fade_out_duration=None):
    def duration(requested):
        return min(requested, clip.duration / 2) if requested is not None else clip.duration * 0.2

    if fade_in:
        clip = clip.fadein(duration(fade_in_duration))
    if fade_out:
        clip = clip.fadeout(duration(fade_out_duration))
    return clip


def compose_transitions(clips, transitions, *, opening_duration=None):
    """Blend visuals without overlapping narration or shifting subtitle timing."""
    prepared = []
    for index, clip in enumerate(clips):
        style, duration = transitions[index]
        previous_style, previous_duration = transitions[index - 1] if index else ("FADE", opening_duration)
        prepared.append(apply_fades(clip, fade_in=previous_style == "FADE", fade_out=style == "FADE",
                                    fade_in_duration=previous_duration, fade_out_duration=duration))
    clips = prepared
    base = concatenate_videoclips(clips)
    overlays = []
    boundary = 0
    for index, (style, duration) in enumerate(transitions[:-1]):
        outgoing, incoming = clips[index:index + 2]
        boundary += outgoing.duration
        if style != "DISSOLVE":
            continue
        duration = min(duration if duration is not None else 0.5,
                       outgoing.duration / 2, incoming.duration / 2)
        if duration <= 0:
            continue
        # Hold the outgoing visual over the opening of the next scene, then
        # reveal the incoming visual with an opacity fade rather than black.
        frame = outgoing.get_frame(max(0, outgoing.duration - 1 / 24))
        overlay = ImageClip(frame).set_duration(duration).crossfadeout(duration).set_start(boundary)
        overlays.append(overlay)
    if not overlays:
        return base, prepared
    return CompositeVideoClip([base, *overlays], size=base.size).set_duration(base.duration), [*prepared, base, *overlays]
