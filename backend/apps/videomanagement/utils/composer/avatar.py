import os
import shlex
import subprocess
import logging

from moviepy.editor import (
    VideoFileClip,
    CompositeVideoClip,
)

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

    try:
        avatar_cam = lip(
            source_image=avatar.file.path,
            driven_audio=os.path.join(dir_name, "output_audio.wav"),
            result_dir=dir_name,
            facerender="pirender",
        )
    except Exception as e:
        logger.error(f"Error running lip function: {e}")
        return ""

    output = os.path.join(os.getcwd(), dir_name, "output_avatar.mp4")

    ffmpeg_command = (
        f'ffmpeg -i "{os.path.join(os.getcwd(), avatar_cam)}" -vcodec h264 "{output}"'
    )
    try:
        result = subprocess.run(
            shlex.split(ffmpeg_command),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            logger.error(f"FFmpeg error: {result.stderr}")
            return ""
    except Exception as e:
        logger.error(f"Error executing ffmpeg: {e}")
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

    avatar_video = f"{os.getcwd()}/{video.dir_name}/output_avatar.mp4"

    if not os.path.exists(f"{os.getcwd()}/{video.dir_name}/output_avatar.mp4"):
        logger.info("Start creating the avatar video")
        avatar_video = create_avatar_video(video.avatar, video.dir_name)

    position = tuple(video.settings.get("avatar_position", "right,top").split(","))
    avatar_vid = (
        VideoFileClip(avatar_video)
        .without_audio()
        .set_position(position)
        .resize(1.5)
        .fadein(2)
        .fadeout(2)
    )

    final_video = CompositeVideoClip([final_video, avatar_vid], size=(1920, 1080))
    return final_video
