"""Stage the same bundled fonts used by browser previews for libass exports."""
import json
import shutil
from pathlib import Path

FONT_DIRECTORY = Path(__file__).resolve().parents[3] / "assets" / "fonts"
FONT_MANIFEST = json.loads((FONT_DIRECTORY / "manifest.json").read_text(encoding="utf-8"))
FONT_FAMILIES = tuple(font["family"] for font in FONT_MANIFEST)


def subtitles_filter(filename, directory):
    # Fixed relative paths avoid FFmpeg filter escaping issues with checkout paths.
    target = Path(directory, "fonts")
    if not target.exists():
        shutil.copytree(FONT_DIRECTORY, target)
    return f"subtitles=filename={filename}:fontsdir=fonts"
