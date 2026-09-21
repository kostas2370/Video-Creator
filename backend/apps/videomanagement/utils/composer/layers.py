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


logger = logging.getLogger(__name__)


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
    music_volume = video.settings.get("music_volume", 0.07)
    music = music.volumex(music_volume)

    if music.duration < duration:
        loop_count = int(duration // music.duration) + 1
        music = concatenate_audioclips([music] * loop_count).subclip(0, duration)

    else:
        music = music.subclip(0, duration)

    fade_duration = min(4, duration * 0.1)
    music = music.audio_fadein(fade_duration).audio_fadeout(fade_duration)

    # With narration switched off the music is the whole soundtrack.
    return CompositeAudioClip([final_audio, music]) if final_audio else music


def handle_background(duration, background, final_video):
    """
    Adds a background effect to a video clip based on the specified color and threshold.

    Args:
        final_audio (AudioFileClip): The final audio clip to synchronize with the video.
        background (Background): The background object containing color and threshold settings for masking.
        final_video (VideoFileClip): The final video clip onto which the masked video will be composited.

    Returns:
        VideoFileClip: The final video with background effect applied, including masking and fade effects.
    """

    if not background:
        return final_video.resize((1920, 1080))

    if background.file.path.lower().endswith((".jpg", ".png")):
        bg_clip = ImageClip(background.file.path)
    else:
        bg_clip = VideoFileClip(background.file.path).without_audio()

    bg_clip = bg_clip.set_duration(duration).resize((1920, 1080))
    mask_color = [int(x) for x in background.color.split(",")]
    threshold = float(background.through) / 255.0
    masked_clip = final_video.fx(vfx.mask_color, color=mask_color, thr=threshold, s=7)
    final_video = CompositeVideoClip(
        [bg_clip, masked_clip.set_duration(duration)]
    ).crossfadein(2)

    return final_video
