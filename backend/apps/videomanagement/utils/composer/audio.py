"""Native voice filters and a bounded music envelope for the FFmpeg compositor."""
import math
import numpy as np

from ..audio_editing import music_gain
from .effects import audio_fade_filters


def voice_stream(graph, path, track):
    index = graph.input(path)
    start = track["trim_start"]
    filters = ["aresample=44100", "aformat=sample_fmts=fltp:channel_layouts=stereo",
               f"atrim=start={start}:end={start + track['duration']}",
               "asetpts=PTS-STARTPTS", f"volume={track['volume']}"]
    filters.extend(audio_fade_filters(track["duration"], fade_in=track["fade_in"], fade_out=track["fade_out"]))
    if track["start"] > 0:
        filters.append(f"adelay={round(track['start'] * 44100)}S:all=1")
    return graph.filter([f"{index}:a"], ",".join(filters))


def write_music_envelope(path, duration, choices, speech):
    """Write one second at a time to keep render memory independent of duration."""
    rate = 44100
    count = math.ceil(duration * rate)
    attack, release = choices.get("duck_attack", 0.2), choices.get("duck_release", 0.8)
    with open(path, "wb") as output:
        for first in range(0, count, rate):
            last = min(first + rate, count)
            relevant = [(a, b) for a, b in speech if b + release >= first / rate and a - attack <= last / rate]
            gain = music_gain(np.arange(first, last) / rate, duration, choices, relevant)
            output.write(np.repeat(gain[:, None], 2, axis=1).astype("<f4").tobytes())
