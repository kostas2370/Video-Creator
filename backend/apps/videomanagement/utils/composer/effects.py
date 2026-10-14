"""Shared audio effects for voice clips and background music."""


def apply_audio_fades(clip, *, fade_in=0, fade_out=0):
    """Keep zero-length fades disabled and cap fades at half the clip length."""
    limit = clip.duration / 2
    if fade_in > 0 and limit > 0:
        clip = clip.audio_fadein(min(fade_in, limit))
    if fade_out > 0 and limit > 0:
        clip = clip.audio_fadeout(min(fade_out, limit))
    return clip
