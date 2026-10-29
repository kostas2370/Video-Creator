import logging
import tempfile
from pathlib import Path

from django.core.files import File
from django.db import transaction
from django.utils import timezone

from apps.videomanagement.utils.captions.cues import word_cues
from apps.videomanagement.utils.captions.styles import project_caption_style
from apps.videomanagement.utils.composer.captions import write_ass
from apps.videomanagement.utils.fonts import subtitles_filter

from .choices import ClipLayout, ClipStatus
from .media import run_ffmpeg
from .models import Clip

logger = logging.getLogger(__name__)


def framing_filter(clip):
    if clip.layout == ClipLayout.CROP:
        return f"[0:v]scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280:(iw-ow)*{clip.crop_position / 100:.6f}:(ih-oh)/2,setsar=1[framed]"
    return (
        "[0:v]split=2[back][front];"
        "[back]scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,boxblur=20:2[blurred];"
        "[front]scale=720:1280:force_original_aspect_ratio=decrease[foreground];"
        "[blurred][foreground]overlay=(W-w)/2:(H-h)/2,setsar=1[framed]"
    )


def export_clip(clip_id, token):
    rows = Clip.objects.filter(pk=clip_id, job_id=token)
    if not rows.filter(status=ClipStatus.QUEUED).update(
        status=ClipStatus.RENDERING, updated_at=timezone.now()
    ):
        return
    clip = rows.select_related("project__created_by").get()
    try:
        if not clip.project.created_by.is_active:
            raise ValueError("Inactive account")
        with tempfile.TemporaryDirectory(prefix="clip-export-") as directory:
            graph = framing_filter(clip)
            if clip.captions and clip.words:
                style = project_caption_style(clip)
                write_ass(
                    Path(directory, "captions.ass"),
                    word_cues(clip.words, style, highlight=True),
                    (720, 1280),
                    style,
                )
                graph += (
                    ";[framed]" + subtitles_filter("captions.ass", directory) + "[out]"
                )
            else:
                graph += ";[framed]null[out]"
            output = Path(directory, "clip.mp4")
            run_ffmpeg(
                [
                    "-ss",
                    str(clip.start),
                    "-i",
                    clip.project.source.path,
                    "-t",
                    str(clip.end - clip.start),
                    "-filter_complex",
                    graph,
                    "-map",
                    "[out]",
                    "-map",
                    "0:a:0",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "fast",
                    "-crf",
                    "21",
                    "-pix_fmt",
                    "yuv420p",
                    "-r",
                    "30",
                    "-c:a",
                    "aac",
                    "-movflags",
                    "+faststart",
                    str(output),
                ],
                cwd=directory,
                timeout=1100,
            )
            with output.open("rb") as file:
                name = clip.output.storage.save(
                    f"media/clips/{clip.project_id}/{clip.pk}/{token}.mp4", File(file)
                )
            with transaction.atomic():
                current = (
                    rows.select_for_update().filter(status=ClipStatus.RENDERING).first()
                )
                if current is None:
                    clip.output.storage.delete(name)
                    return
                previous = current.output.name
                rows.update(
                    output=name,
                    status=ClipStatus.COMPLETED,
                    error="",
                    updated_at=timezone.now(),
                )
                if previous and previous != name:
                    transaction.on_commit(
                        lambda: clip.output.storage.delete(previous), robust=True
                    )
    except Exception:
        logger.exception("Clip export failed for %s", clip_id)
        rows.filter(status=ClipStatus.RENDERING).update(
            status=ClipStatus.FAILED,
            error="Could not export this clip. Please retry.",
            updated_at=timezone.now(),
        )
