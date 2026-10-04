DEFAULT_VIDEO_FORMAT = "LANDSCAPE"
DEFAULT_VIDEO_PLATFORM = "GENERAL"

VIDEO_PLATFORM_CHOICES = (
    ("GENERAL", "General video"),
    ("TIKTOK", "TikTok"),
)

VIDEO_FORMAT_CHOICES = (
    ("LANDSCAPE", "Landscape (16:9)"),
    ("PORTRAIT", "Portrait (9:16)"),
    ("SQUARE", "Square (1:1)"),
)

VIDEO_FORMAT_SIZES = {
    "LANDSCAPE": (1920, 1080),
    "PORTRAIT": (1080, 1920),
    "SQUARE": (1080, 1080),
}


def output_size(video_format):
    """Return the render canvas, defaulting old videos to the original landscape size."""
    return VIDEO_FORMAT_SIZES.get(video_format, VIDEO_FORMAT_SIZES[DEFAULT_VIDEO_FORMAT])
