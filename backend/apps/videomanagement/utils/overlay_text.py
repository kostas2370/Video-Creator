"""Fit overlay text using the selected font, retaining deliberate line breaks."""
import re
from functools import lru_cache

from PIL import ImageFont

from .fonts import FONT_DIRECTORY, FONT_MANIFEST

TEXT_WIDTH = 88
LINE_HEIGHT = 1.5


@lru_cache(maxsize=16)
def overlay_font(family):
    definition = next((font for font in FONT_MANIFEST if font["family"] == family), FONT_MANIFEST[0])
    face = max(definition["faces"], key=lambda item: item["weight"])
    path = str(FONT_DIRECTORY / face["file"]) if definition["bundled"] else face["file"]
    return ImageFont.truetype(path, 1000)


def wrap_text(text, size, measure):
    paragraphs = []
    for paragraph in text.split("\n"):
        lines, current = [], ""
        for word in re.findall(r"\S+", paragraph):
            candidate = f"{current} {word}" if current else word
            if measure(candidate) * size <= TEXT_WIDTH:
                current = candidate
                continue
            if current:
                lines.append(current)
                current = ""
            for character in word:
                if current and measure(current + character) * size > TEXT_WIDTH:
                    lines.append(current)
                    current = ""
                current += character
        lines.append(current)
        paragraphs.extend(lines)
    return "\n".join(paragraphs)


def overlay_text_layout(text, size, family, frame_size):
    font = overlay_font(family)

    @lru_cache(maxsize=4096)
    def measure(line):
        bounds = font.getbbox(line)
        return max(font.getlength(line), bounds[2] - bounds[0]) / 1000

    max_height = 88 * frame_size[1] / frame_size[0]

    def layout(value):
        wrapped = wrap_text(text, value, measure)
        return wrapped, len(wrapped.split("\n")) * value * LINE_HEIGHT <= max_height

    wrapped, fits = layout(size)
    if fits:
        return wrapped, size
    low, high = 0, size
    for _ in range(20):
        middle = (low + high) / 2
        _, fits = layout(middle)
        if fits:
            low = middle
        else:
            high = middle
    return layout(low)[0], low
