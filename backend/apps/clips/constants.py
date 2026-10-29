from datetime import timedelta

MAX_CLIPS_PER_PROJECT = 20
MAX_CLIP_DURATION = 180
MAX_CAPTION_WORDS = 10000
STALE_AFTER = timedelta(hours=3)

CLIP_RENDER_FIELDS = (
    "start",
    "end",
    "layout",
    "crop_position",
    "captions",
    "words",
    "style",
)
