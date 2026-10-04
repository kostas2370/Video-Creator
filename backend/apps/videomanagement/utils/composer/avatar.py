import os
import subprocess
import logging

from moviepy.editor import (
    VideoFileClip,
    CompositeVideoClip,
)

from vendor.sadtalker.inference import lip
from ...models import Avatar

logger = logging.getLogger(__name__)


def _fade_overlay_opacity(clip, fade_duration=0.5):
    """Fade an overlay through its mask so the video beneath remains visible."""
    duration = clip.duration
    if not duration or duration <= 0:
        return clip

    fade_duration = min(fade_duration, duration / 2)
    clip = clip.add_mask()

    def fade_mask(get_frame, time):
        opacity = max(
            0.0,
            min(1.0, time / fade_duration, (duration - time) / fade_duration),
        )
        return get_frame(time) * opacity

    return clip.set_mask(clip.mask.fl(fade_mask))


def create_avatar_video(avatar: Avatar, dir_name: str) -> str:
    """
    Create an avatar video synchronized with an audio file.

    Parameters:
    -----------
    avatar : Avatars
        An instance of the Avatars class containing the avatar image file.
    dir_name : str
        The directory name where the output files are stored.

    Returns:
    --------
    str
        The file path to the created avatar video.

    Detailed Steps:
    ---------------
    1. Use the `lip` function to generate a video of the avatar synchronized with the audio file.
    2. Use ffmpeg to encode the generated video with the h264 codec and save it to the specified directory.

    Notes:
    ------
    - Requires the `lip` function and ffmpeg to be properly installed and configured.
    - The `lip` function should generate the avatar video and save it in the specified directory.
    """

    video_dir = os.path.abspath(dir_name)
    audio_path = os.path.join(video_dir, "output_audio.wav")
    if not os.path.isfile(audio_path):
        logger.error(
            "Cannot create avatar video: narration audio is missing at %s", audio_path
        )
        return ""

    try:
        avatar_cam = lip(
            source_image=avatar.file.path,
            driven_audio=audio_path,
            result_dir=video_dir,
            facerender="pirender",
        )
    except Exception:
        logger.exception("SadTalker failed to create an avatar video")
        return ""

    if not avatar_cam:
        logger.error("SadTalker returned no avatar video for %s", avatar.pk)
        return ""

    avatar_cam_path = avatar_cam if os.path.isabs(avatar_cam) else os.path.abspath(avatar_cam)
    output = os.path.join(video_dir, "output_avatar.mp4")

    try:
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", avatar_cam_path, "-vcodec", "h264", output],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            logger.error("FFmpeg could not encode the SadTalker output: %s", result.stderr)
            return ""
    except Exception:
        logger.exception("Failed to run ffmpeg for the avatar video")
        return ""

    return output


def handle_avatar_video(video, final_video):
    """
    Adds an avatar video to the final video, positioning it at the top right and applying fade-in and fade-out effects.

    This function handles the addition of an avatar video by:
    1. Checking if the avatar video file exists; if not, it creates the avatar video.
    2. Loading the avatar video, removing its audio, resizing it, and applying fade effects.
    3. Compositing the avatar video onto the final video at the specified position and size.

    Args:
        video (Video): The video object containing metadata and the directory name for the avatar video.
        final_video (VideoFileClip): The final video clip onto which the avatar video will be composited.

    Returns:
        VideoFileClip: The final video clip with the avatar video composited at the top right corner, with fade-in
                       and fade-out effects applied.
    """

    avatar_video = os.path.join(os.path.abspath(video.dir_name), "output_avatar.mp4")

    if not os.path.exists(avatar_video):
        logger.info("Start creating the avatar video")
        avatar_video = create_avatar_video(video.avatar, video.dir_name)

    if not avatar_video or not os.path.exists(avatar_video):
        logger.error("No avatar video for %s; rendering without it", video.pk)
        return final_video

    settings = video.settings or {}
    avatar_vid = (
        VideoFileClip(avatar_video)
        .without_audio()
        .set_position(tuple(settings.get("avatar_position", "right,top").split(",")))
        .resize(1.5)
    )
    avatar_vid = _fade_overlay_opacity(avatar_vid, fade_duration=0.5)

    final_video = CompositeVideoClip([final_video, avatar_vid], size=final_video.size)
    return final_video
