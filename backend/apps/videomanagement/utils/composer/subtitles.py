import logging

from django.conf import settings
from moviepy.editor import (
    TextClip,
)


logger = logging.getLogger(__name__)


def create_subtitle_clip(
    text: str,
    duration: float,
    fontsize: int = 48,
    color: str = "white",
    bg_color: str = "transparent",
    font: str = None,
    size: tuple = (1600, 200),
    stroke_color: str = "black",
    stroke_width: int = 2,
) -> TextClip:
    """
    Creates a styled subtitle clip.

    Parameters:
    -----------
    text : str
        The subtitle text.
    duration : float
        The duration for which the subtitle should be displayed.
    fontsize : int, optional
        The font size of the text (default: 48).
    color : str, optional
        The color of the text (default: "white").
    bg_color : str, optional
        The box background (default: "transparent"). An opaque colour paints the whole
        `size` rectangle over the picture.
    font : str, optional
        The ImageMagick font name. Defaults to settings.SUBTITLE_FONT.
    size : tuple, optional
        The subtitle box, (width, height) (default: (1600, 200)). `method="caption"`
        centres the text vertically inside it, so an over-tall box pushes the text
        off-screen.
    stroke_color, stroke_width : optional
        Glyph outline, which keeps the text readable over light imagery.

    Returns:
    --------
    TextClip
        A moviepy TextClip styled as a subtitle.
    """
    try:
        return TextClip(
            text,
            fontsize=fontsize,
            color=color,
            font=font or settings.SUBTITLE_FONT,
            method="caption",
            size=size,
            bg_color=bg_color,
            stroke_color=stroke_color,
            stroke_width=stroke_width,
        ).set_duration(duration)
    except Exception as e:
        logger.error(f"Error creating subtitle clip: {e}")
        return None
