"""Create covers from video frames, generated images, or uploads."""

import subprocess
import tempfile
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from django.core.files.base import ContentFile
from django.db import transaction
from PIL import Image, ImageDraw, ImageFont, ImageOps
from rest_framework.exceptions import ValidationError

from apps.videomanagement.integrations.visuals import openai_images
from apps.videomanagement.models import SceneImage, Video
from apps.videomanagement.utils.file_utils import check_if_video, stored_file_exists
from apps.videomanagement.utils.fonts import FONT_DIRECTORY
from apps.videomanagement.utils.prompt_utils import format_cover_prompt
from apps.videomanagement.utils.timing import media_timing

FONT_FILES = {
    "Poppins": "Poppins-Bold.ttf",
    "Lato": "Lato-Bold.ttf",
    "Bebas Neue": "BebasNeue-Regular.ttf",
    "DejaVu Sans": "DejaVuSans-Bold.ttf",
    "DejaVu Serif": "DejaVuSerif-Bold.ttf",
    "DejaVu Sans Mono": "DejaVuSansMono-Bold.ttf",
}


def cover_font(family, size):
    filename = FONT_FILES[family]
    bundled = FONT_DIRECTORY / filename
    try:
        return ImageFont.truetype(str(bundled) if bundled.exists() else filename, size)
    except OSError:
        raise ValidationError(
            {"font": "This font could not be loaded on the renderer."}
        )


def frame_image(video, time):
    if video.status == "RENDERING" or not stored_file_exists(video.output):
        raise ValidationError("Export the video before creating a cover.")
    duration = media_timing(video.output.path).get("duration")
    if not duration or time >= duration:
        raise ValidationError({"time": "Choose a frame within the exported video."})
    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-nostdin",
                "-ss",
                str(time),
                "-i",
                video.output.path,
                "-frames:v",
                "1",
                "-vf",
                "scale='min(1280,iw)':'min(1280,ih)':force_original_aspect_ratio=decrease",
                "-f",
                "image2pipe",
                "-vcodec",
                "png",
                "pipe:1",
            ],
            capture_output=True,
            check=True,
            timeout=30,
        )
        return Image.open(BytesIO(result.stdout)).convert("RGBA")
    except (OSError, ValueError, subprocess.SubprocessError):
        raise ValidationError(
            "Could not read this frame. Choose a slightly earlier time and try again."
        )


def cover_reference(video, directory, time=0):
    """Prefer the video's visual identity and scene art over branded intros."""
    candidates = [video.reference_image]
    candidates.extend(
        visual.file
        for visual in SceneImage.objects.filter(scene__video=video)
        .exclude(file="")
        .exclude(file__isnull=True)
        .order_by("scene__position", "created_at", "id")
    )
    for candidate in candidates:
        if not stored_file_exists(candidate) or check_if_video(candidate.name):
            continue
        try:
            with Image.open(candidate.path) as image:
                image.verify()
        except (OSError, ValueError):
            continue
        return candidate.path
    if not stored_file_exists(video.output):
        return None
    if not time:
        duration = media_timing(video.output.path).get("duration", 0)
        intro, outro = (_asset_duration(asset) for asset in (video.intro, video.outro))
        time = (
            (intro + duration - outro) / 2 if duration > intro + outro else duration / 2
        )
    reference = str(Path(directory) / "reference.png")
    frame_image(video, time).save(reference)
    return reference


def _asset_duration(asset):
    if not asset or not stored_file_exists(asset.file):
        return 0
    return media_timing(asset.file.path).get("duration", 0)


def generate_cover_image(video, user, choices):
    scenes = list(video.scenes.order_by("position").values_list("text", flat=True))
    content = {
        "title": video.title,
        "content": scenes or video.gpt_answer or video.prompt.prompt,
    }
    prompt = format_cover_prompt(content, choices.get("title", ""), choices["prompt"])
    with tempfile.TemporaryDirectory() as directory:
        reference = cover_reference(video, directory, choices["time"])
        path = openai_images.generate_openai_image(
            prompt, directory + "/", style="", user=user, reference=reference
        )
        with Image.open(path) as image:
            image = ImageOps.fit(
                image.convert("RGB"), (1280, 720), method=Image.Resampling.LANCZOS
            )
            output = BytesIO()
            image.save(output, format="PNG")
            return output.getvalue()


def create_cover(video, choices):
    if choices.get("source", "frame") == "frame":
        image = frame_image(video, choices["time"])
    else:
        uploaded = choices["image"]
        uploaded.seek(0)
        with Image.open(uploaded) as source:
            image = ImageOps.exif_transpose(source).convert("RGBA")
        image.thumbnail((1280, 1280))
    # AI thumbnails already contain their title; never draw it a second time.
    title = "" if choices.get("source") == "ai" else choices["title"].strip()
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
                    if current and draw.textlength(candidate, font=font) > width * 0.84:
                        lines.append(current)
                        current = word
                    else:
                        current = candidate
                lines.append(current)
            text = "\n".join(lines)
            stroke = max(1, font_size // 22)
            box = draw.multiline_textbbox(
                (0, 0), text, font=font, spacing=font_size // 5, stroke_width=stroke
            )
            tw, th = box[2] - box[0], box[3] - box[1]
            if tw <= width * 0.86 and th <= height * 0.65:
                break
            if font_size <= 6:
                raise ValidationError(
                    {"title": "Use a shorter title so it fits within the cover."}
                )
            font_size -= 1
        x = (width - tw) / 2 - box[0]
        top = {
            "top": height * 0.08,
            "middle": (height - th) / 2,
            "bottom": height * 0.92 - th,
        }[choices["position"]]
        y = top - box[1]
        if choices["background"]:
            layer = Image.new("RGBA", image.size)
            ImageDraw.Draw(layer).rounded_rectangle(
                (
                    max(0, (width - tw) / 2 - 12),
                    max(0, top - 10),
                    min(width, (width + tw) / 2 + 12),
                    min(height, top + th + 10),
                ),
                radius=8,
                fill=(0, 0, 0, 175),
            )
            image = Image.alpha_composite(image, layer)
            draw = ImageDraw.Draw(image)
        draw.multiline_text(
            (x, y),
            text,
            font=font,
            fill=choices["color"],
            align="center",
            spacing=font_size // 5,
            stroke_width=stroke,
            stroke_fill="black",
        )
    output = BytesIO()
    image.convert("RGB").save(output, format="PNG")
    return output.getvalue()


def save_cover(video, choices):
    with transaction.atomic():
        video = Video.objects.select_for_update().get(pk=video.pk)
        image = create_cover(video, choices)
        old = video.cover.name
        video.cover.save(
            f"{video.pk}-{uuid4().hex}.png", ContentFile(image), save=False
        )
        try:
            video.cover_settings = {
                key: value for key, value in choices.items() if key != "image"
            }
            video.save(update_fields=["cover", "cover_settings"])
        except Exception:
            video.cover.storage.delete(video.cover.name)
            raise
        if old:
            transaction.on_commit(lambda: video.cover.storage.delete(old), robust=True)
    return video
