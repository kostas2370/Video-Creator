import logging

from moviepy.editor import (
    AudioFileClip,
    concatenate_audioclips,
    CompositeAudioClip,
    ImageClip,
    VideoFileClip,
    vfx,
    CompositeVideoClip,
)


from ..audio_editing import voice_tracks, music_gain
from .audio import scene_audio_segments
from .effects import apply_audio_fades
import numpy as np

logger = logging.getLogger(__name__)


def fit_to_canvas(clip, size):
    """Resize and center-crop a clip to fill a canvas without stretching it."""
    target_width, target_height = size
    source_width, source_height = clip.size
    if abs(source_width / source_height - target_width / target_height) < 0.0001:
        return clip.resize(size)
    scale = max(target_width / source_width, target_height / source_height)
    resized = clip.resize(scale)
    resized_width, resized_height = resized.size
    x1 = max(0, (resized_width - target_width) / 2)
    y1 = max(0, (resized_height - target_height) / 2)
    return resized.crop(
        x1=x1,
        y1=y1,
        x2=x1 + target_width,
        y2=y1 + target_height,
    )


def handle_music(video, final_audio, duration):
    """
    Adds background music to the final audio, adjusting the volume and applying fade-in and fade-out effects.

    Args:
        video (Video): The video object containing metadata and the file path for the music.
        final_audio (AudioFileClip): The final audio clip to which the background music will be added.

    Returns:
        AudioFileClip: The final audio clip with the background music added,
        including volume adjustment and fade effects.
    """

    music = AudioFileClip(video.music.file.path)
    music_volume = (video.settings or {}).get("music_volume", 0.07)
    music = music.volumex(music_volume)

    if music.duration < duration:
        loop_count = int(duration // music.duration) + 1
        music = concatenate_audioclips([music] * loop_count).subclip(0, duration)

    else:
        music = music.subclip(0, duration)

    choices = video.settings or {}
    if any(key in choices for key in ("music_ducking", "music_fade_in", "music_fade_out")):
        speech = []
        if choices.get("music_ducking"):
            scenes = list(video.scenes.prefetch_related("scene_images"))
            speech = [interval for track in voice_tracks(scene_audio_segments(scenes)) for interval in track["speech"]]
        # Base volume was applied above; this envelope supplies fades and ducking.
        envelope_choices = {**choices, "music_volume": 1}
        def envelope(get_frame, t):
            gain = music_gain(t, duration, envelope_choices, speech)
            frame = get_frame(t)
            return frame * (gain[:, None] if np.ndim(frame) == 2 and np.ndim(gain) else gain)
        music = music.fl(envelope, keep_duration=True)
    else:
        fade_duration = min(4, duration * 0.1)
        music = apply_audio_fades(music, fade_in=fade_duration, fade_out=fade_duration)

    # With narration switched off the music is the whole soundtrack.
    return CompositeAudioClip([final_audio, music]) if final_audio else music


def handle_background(duration, background, final_video, size=(1920, 1080)):
    """
    Adds a background effect to a video clip based on the specified color and threshold.

    Args:
        final_audio (AudioFileClip): The final audio clip to synchronize with the video.
        background (Background): The background object containing color and threshold settings for masking.
        final_video (VideoFileClip): The final video clip onto which the masked video will be composited.

    Returns:
        VideoFileClip: The final video with background effect applied, including masking and fade effects.
    """

    final_video = fit_to_canvas(final_video, size)
    if not background:
        return final_video

    if background.file.path.lower().endswith((".jpg", ".png")):
        bg_clip = ImageClip(background.file.path)
    else:
        bg_clip = VideoFileClip(background.file.path).without_audio()

    bg_clip = fit_to_canvas(bg_clip, size).set_duration(duration)
    mask_color = [int(x) for x in background.color.split(",")]
    threshold = float(background.through) / 255.0
    masked_clip = final_video.fx(vfx.mask_color, color=mask_color, thr=threshold, s=7)
    final_video = CompositeVideoClip(
        [bg_clip, masked_clip.set_duration(duration)], size=size
    ).crossfadein(2)

    return final_video
