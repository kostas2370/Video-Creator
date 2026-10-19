import logging
import subprocess
import uuid
from pathlib import Path

from .file_utils import check_if_video
from .timing import video_metadata

logger = logging.getLogger(__name__)


def still_from_video(path: str, dir_name: str, end_time: float = None) -> str:
    """Save the last frame of `path` as a png, or return None if it is not a video.

    Used as the opening frame for the next clip in the sequence.
    """
    if not check_if_video(path):
        return None

    frame_path = f"{dir_name}{uuid.uuid4()}.png"
    try:
        metadata = video_metadata(path)
        end = min(metadata["duration"], end_time) if end_time else metadata["duration"]
        for timestamp in (end - 1 / metadata["fps"], end * 0.5, 0):
            try:
                save_video_frame(path, frame_path, max(0, timestamp))
                return frame_path
            except (OSError, subprocess.SubprocessError) as exc:
                logger.debug("No frame at %.2fs of %s: %s", timestamp, path, exc)
    except (
        OSError,
        ValueError,
        KeyError,
        StopIteration,
        subprocess.SubprocessError,
    ) as exc:
        logger.warning("Could not open %s for a style anchor: %s", path, exc)
    Path(frame_path).unlink(missing_ok=True)
    return None


def save_video_frame(source, destination, timestamp):
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
            "-y",
            "-ss",
            str(timestamp),
            "-i",
            str(source),
            "-frames:v",
            "1",
            "-update",
            "1",
            str(destination),
        ],
        check=True,
        capture_output=True,
        timeout=30,
    )
    if not Path(destination).is_file():
        raise OSError("No video frame decoded")
