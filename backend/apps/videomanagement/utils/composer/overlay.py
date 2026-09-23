import os
import subprocess
import uuid
import logging


logger = logging.getLogger(__name__)


def add_text_to_video(
    video: str,
    text: str,
    fontcolor: str = "black",
    fontsize: int = 50,
    x: str = "(w-text_w)/2",
    y: str = "h-text_h-20",
) -> str:
    """
    Add text to a video at a specified position and return the new video file path.

    Parameters:
    -----------
    video : str
        The file path to the original video.
    text : str
        The text to be added to the video.
    fontcolor : str, optional
        The color of the text. Default is "black".
    fontsize : int, optional
        The size of the text font. Default is 50.
    x : str, optional
        The x-coordinate position for the text (FFmpeg expression). Default is centered.
    y : str, optional
        The y-coordinate position for the text (FFmpeg expression). Default is near the bottom.

    Returns:
    --------
    str
        The file path to the new video with the added text.

    Detailed Steps:
    ---------------
    1. Generate a new file name for the video with the added text.
    2. Construct the ffmpeg command to add text to the video.
    3. Execute the ffmpeg command using subprocess.
    4. Remove the original video file if successful.
    5. Return the file path to the new video.

    Notes:
    ------
    - Requires ffmpeg to be installed and available in the system path.
    - The original video file is deleted only if the new video is successfully created.
    """

    base_dir, ext = os.path.splitext(video)
    output_video = f"{base_dir}_{uuid.uuid4().hex}.mp4"

    text_path = f"{base_dir}_{uuid.uuid4().hex}.txt"
    with open(text_path, "w", encoding="utf-8") as handle:
        handle.write(text)

    command = [
        "ffmpeg",
        "-i",
        video,
        "-vf",
        f"drawtext=fontsize={fontsize}:fontcolor={fontcolor}:textfile={text_path}:"
        f"x={x}:y={y}:shadowcolor=black:shadowx=2:shadowy=2:"
        f"box=1:boxcolor=black@0.5:boxborderw=10",
        "-y",
        output_video,
    ]
    try:
        result = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        if result.returncode != 0:
            logger.error(f"FFmpeg error: {result.stderr}")
            return ""

        os.remove(video)
        return output_video

    except Exception as e:
        logger.error(f"Error processing video: {e}")
        return ""

    finally:
        if os.path.exists(text_path):
            os.remove(text_path)
