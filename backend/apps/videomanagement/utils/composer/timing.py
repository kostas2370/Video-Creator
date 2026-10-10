"""Keep scene visuals, audio, and pauses on the same timeline."""
import numpy as np
from moviepy.editor import AudioClip, CompositeAudioClip, ImageClip, concatenate_videoclips


def hold_scene(clip, pause):
    if not pause:
        return clip, []
    frame = clip.get_frame(max(0, clip.duration - 1 / (getattr(clip, "fps", None) or 24)))
    hold = ImageClip(frame).set_duration(pause)
    extended = concatenate_videoclips([clip, hold], method="compose")
    return extended, [clip, hold]


def align_audio(audio, duration):
    if audio is not None and abs(audio.duration - duration) < 0.000001:
        return audio
    if audio is not None:
        return CompositeAudioClip([audio]).set_duration(duration)
    return AudioClip(lambda t: np.zeros((len(t), 2)) if isinstance(t, np.ndarray) else np.zeros(2),
                     duration=duration, fps=44100)
