import logging
import subprocess
import uuid
from pathlib import Path

from apps.common.media import run_ffmpeg

from .file_utils import check_if_video
from .timing import video_metadata

logger = logging.getLogger(__name__)


def extract_video_frame(source, timestamp, *, max_size=1280, codec="png", timeout=30):
    """Return an encoded frame, scaled to fit a square without enlarging it."""
    result = run_ffmpeg(
        [
            "-threads",
            "1",
            "-ss",
            str(timestamp),
            "-i",
            str(source),
            "-frames:v",
            "1",
            "-vf",
            f"scale='min({max_size},iw)':'min({max_size},ih)':force_original_aspect_ratio=decrease",
            *(["-q:v", "4"] if codec == "mjpeg" else []),
            "-threads",
            "1",
            "-f",
            "image2pipe",
            "-vcodec",
            codec,
            "pipe:1",
        ],
        timeout=timeout,
    )
    return result.stdout


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
    run_ffmpeg(
        [
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
        timeout=30,
    )
    if not Path(destination).is_file():
        raise OSError("No video frame decoded")
