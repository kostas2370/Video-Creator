"""Stage the same bundled fonts used by browser previews for libass exports."""
from pathlib import Path
import shutil

FONT_DIRECTORY = Path(__file__).resolve().parents[3] / "assets" / "fonts"


def subtitles_filter(filename, directory):
    # Fixed relative paths avoid FFmpeg filter escaping issues with checkout paths.
    target = Path(directory, "fonts")
    if not target.exists():
        shutil.copytree(FONT_DIRECTORY, target)
    return f"subtitles=filename={filename}:fontsdir=fonts"
