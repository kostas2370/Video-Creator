"""Shared native audio fade filters for voices and background music."""


def audio_fade_filters(duration, *, fade_in=0, fade_out=0):
    filters = []
    incoming = min(fade_in, duration / 2)
    outgoing = min(fade_out, duration / 2)
    if incoming > 0:
        filters.append(f"afade=t=in:st=0:d={incoming}")
    if outgoing > 0:
        filters.append(f"afade=t=out:st={duration - outgoing}:d={outgoing}")
    return filters
