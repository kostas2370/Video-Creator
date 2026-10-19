"""Caption appearance and grouping, independent of the renderer or preset name."""
from dataclasses import asdict, dataclass, replace

from django.conf import settings

FONTS = ("DejaVu Sans", "DejaVu Serif", "DejaVu Sans Mono", "Poppins", "Lato", "Bebas Neue")


@dataclass(frozen=True)
class CaptionStyle:
    name: str = "Custom"
    font: str = "DejaVu Sans"
    font_size: float = 6
    scale_with_frame: bool = True
    color: str = "#ffffff"
    highlight_color: str = "#ffe846"
    outline_color: str = "#000000"
    outline_width: float = 0.45
    shadow: float = 0.2
    bold: bool = True
    uppercase: bool = True
    highlight_words: bool = True
    position: str = "bottom"
    margin_left: float = 8
    margin_right: float = 14
    margin_vertical: float = 9
    portrait_margin_vertical: float = 22
    line_width: int = 20
    max_words: int = 4
    max_characters: int = 38

    def to_dict(self):
        return asdict(self)

    def text_scale(self, text, size):
        longest = max((len(line) for line in text.splitlines()), default=1)
        font_percent = self.layout(size)["font_size"] * 100 / size[0]
        available = 100 - self.margin_left - self.margin_right
        return min(1, available / (max(1, longest) * font_percent * 0.6))

    def layout(self, size):
        width, height = size
        scale = min(size) / 100 if self.scale_with_frame else 1
        vertical = self.portrait_margin_vertical if height > width and self.position == "bottom" else self.margin_vertical
        return {
            "font_size": round(self.font_size * scale, 2),
            "outline": round(self.outline_width * scale, 2),
            "shadow": round(self.shadow * scale, 2),
            "alignment": {"bottom": 2, "middle": 5, "top": 8}[self.position],
            "margin_left": int(width * self.margin_left / 100),
            "margin_right": int(width * self.margin_right / 100),
            "margin_vertical": 0 if self.position == "middle" else int(height * vertical / 100),
        }


# Adding a built-in style changes this registry, not the rendering pipeline.
CAPTION_STYLES = {
    "CLASSIC": CaptionStyle(name="Classic", font_size=48, scale_with_frame=False,
                            outline_width=2, shadow=0, bold=False, uppercase=False,
                            highlight_words=False, margin_right=8, margin_vertical=5,
                            portrait_margin_vertical=5, line_width=32, max_words=10, max_characters=62),
    "TIKTOK": CaptionStyle(name="TikTok"),
}
CUSTOM_STYLE = CaptionStyle()


def resolve_style(preset="TIKTOK", custom=None):
    if isinstance(preset, CaptionStyle):
        return preset
    if preset == "CUSTOM":
        return replace(CUSTOM_STYLE, **(custom or {}))
    return replace(CAPTION_STYLES.get(preset, CAPTION_STYLES["CLASSIC"]), font=settings.SUBTITLE_FONT)


def caption_style(video):
    choices = video.settings or {}
    return choices.get("caption_style") or ("TIKTOK" if choices.get("platform") == "TIKTOK" else "CLASSIC")


def video_caption_style(video):
    return resolve_style(caption_style(video), (video.settings or {}).get("caption_config"))


def style_catalog():
    return {"presets": {key: resolve_style(key).to_dict() for key in CAPTION_STYLES},
            "custom_defaults": CUSTOM_STYLE.to_dict(), "fonts": list(FONTS)}
