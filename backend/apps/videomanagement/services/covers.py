"""Create title covers from actual exported video frames."""
from io import BytesIO
import subprocess

from PIL import Image, ImageDraw, ImageFont
from rest_framework.exceptions import ValidationError

from ..utils.file_utils import stored_file_exists
from ..utils.fonts import FONT_DIRECTORY
from ..utils.timing import media_timing

FONT_FILES = {"Poppins": "Poppins-Bold.ttf", "Lato": "Lato-Bold.ttf", "Bebas Neue": "BebasNeue-Regular.ttf",
              "DejaVu Sans": "DejaVuSans-Bold.ttf", "DejaVu Serif": "DejaVuSerif-Bold.ttf", "DejaVu Sans Mono": "DejaVuSansMono-Bold.ttf"}


def cover_font(family, size):
    filename = FONT_FILES[family]
    bundled = FONT_DIRECTORY / filename
    try:
        return ImageFont.truetype(str(bundled) if bundled.exists() else filename, size)
    except OSError:
        raise ValidationError({"font": "This font could not be loaded on the renderer."})


def create_cover(video, choices):
    if video.status == "RENDERING" or not stored_file_exists(video.output):
        raise ValidationError("Export the video before creating a cover.")
    duration = media_timing(video.output.path).get("duration")
    if not duration or choices["time"] >= duration:
        raise ValidationError({"time": "Choose a frame within the exported video."})
    try:
        result = subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-ss", str(choices["time"]),
            "-i", video.output.path, "-frames:v", "1", "-vf", "scale='min(1280,iw)':'min(1280,ih)':force_original_aspect_ratio=decrease",
            "-f", "image2pipe", "-vcodec", "png", "pipe:1"], capture_output=True, check=True, timeout=30)
        image = Image.open(BytesIO(result.stdout)).convert("RGBA")
    except (OSError, ValueError, subprocess.SubprocessError):
        raise ValidationError("Could not read this frame. Choose a slightly earlier time and try again.")
    title = choices["title"].strip()
    if title:
        width, height = image.size
        font_size = max(12, round(width * choices["size"] / 100))
        draw = ImageDraw.Draw(image)
        while True:
            font = cover_font(choices["font"], font_size)
            lines = []
            for paragraph in title.splitlines():
                current = ""
                for word in paragraph.split():
                    candidate = (current + " " + word).strip()
                    if current and draw.textlength(candidate, font=font) > width * .84:
                        lines.append(current)
                        current = word
                    else:
                        current = candidate
                lines.append(current)
            text = "\n".join(lines)
            stroke = max(1, font_size // 22)
            box = draw.multiline_textbbox((0, 0), text, font=font, spacing=font_size // 5, stroke_width=stroke)
            tw, th = box[2] - box[0], box[3] - box[1]
            if tw <= width * .86 and th <= height * .65:
                break
            if font_size <= 6:
                raise ValidationError({"title": "Use a shorter title so it fits within the cover."})
            font_size -= 1
        x = (width - tw) / 2 - box[0]
        top = {"top": height * .08, "middle": (height - th) / 2, "bottom": height * .92 - th}[choices["position"]]
        y = top - box[1]
        if choices["background"]:
            layer = Image.new("RGBA", image.size)
            ImageDraw.Draw(layer).rounded_rectangle((max(0, (width - tw) / 2 - 12), max(0, top - 10), min(width, (width + tw) / 2 + 12), min(height, top + th + 10)), radius=8, fill=(0, 0, 0, 175))
            image = Image.alpha_composite(image, layer)
            draw = ImageDraw.Draw(image)
        draw.multiline_text((x, y), text, font=font, fill=choices["color"], align="center", spacing=font_size // 5, stroke_width=stroke, stroke_fill="black")
    output = BytesIO()
    image.convert("RGB").save(output, format="PNG")
    return output.getvalue()
