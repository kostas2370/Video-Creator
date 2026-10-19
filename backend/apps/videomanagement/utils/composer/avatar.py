import logging
import os
import subprocess

from vendor.sadtalker.inference import lip

from ...models import Avatar

logger = logging.getLogger(__name__)


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

    avatar_cam_path = (
        avatar_cam if os.path.isabs(avatar_cam) else os.path.abspath(avatar_cam)
    )
    output = os.path.join(video_dir, "output_avatar.mp4")

    try:
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", avatar_cam_path, "-vcodec", "h264", output],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            logger.error(
                "FFmpeg could not encode the SadTalker output: %s", result.stderr
            )
            return ""
    except Exception:
        logger.exception("Failed to run ffmpeg for the avatar video")
        return ""

    return output
