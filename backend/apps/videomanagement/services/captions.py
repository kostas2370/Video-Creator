"""Timestamped captions over an uploaded video's original picture and sound."""
import math
import re
import subprocess
import tempfile
from pathlib import Path
from uuid import uuid4

from ..utils.fonts import subtitles_filter

from django.core.files import File
from django.db import transaction
from django.utils import timezone
from openai import OpenAI
from rest_framework.exceptions import APIException

from apps.apikeysmanagement.models import ApiKeys, Provider
from ..models import CaptionProject
from ..utils.usage import record_usage
from ..utils.composer.render import ass_timestamp
from .subtitles import word_cues

BUSY_STATUSES = {"QUEUED", "TRANSCRIBING", "RENDER_QUEUED", "RENDERING"}


class CaptionConflict(APIException):
    status_code = 409
    default_detail = "Wait for caption processing to finish before making changes."


def queue_caption_job(project, *, render=False):
    from ..tasks import caption_project_task

    token = uuid4()
    with transaction.atomic():
        locked = CaptionProject.objects.select_for_update().get(pk=project.pk)
        # A newly uploaded project has no job yet. Jobs older than 30 minutes can be retried.
        if locked.status in BUSY_STATUSES and locked.job_id and (timezone.now() - locked.updated_at).total_seconds() < 1800:
            raise CaptionConflict()
        if render and not locked.words:
            raise CaptionConflict("Add some caption words before exporting.")
        locked.status = "RENDER_QUEUED" if render else "QUEUED"
        locked.job_id, locked.error = token, ""
        locked.save(update_fields=["status", "job_id", "error", "updated_at"])
    try:
        caption_project_task.apply_async(args=(str(project.pk), str(token), render))
    except Exception as exc:
        CaptionProject.objects.filter(pk=project.pk, job_id=token).update(
            status="READY" if locked.words else "FAILED", error="Could not queue processing. Please retry.", updated_at=timezone.now()
        )
        error = APIException("Project saved, but processing could not be queued. Please retry.")
        error.status_code = 503
        raise error from exc
    project.refresh_from_db()
    return project


def run_ffmpeg(arguments, *, cwd=None):
    subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-v", "error", "-y", "-threads", "2", "-filter_threads", "2", *arguments],
                   cwd=cwd, capture_output=True, check=True, timeout=1100)


def transcribe_project(project, directory):
    preview = Path(directory, "preview.mp4")
    run_ffmpeg(["-i", project.source.path, "-map", "0:v:0", "-map", "0:a:0", "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart", str(preview)])
    audio = Path(directory, "speech.mp3")
    run_ffmpeg(["-i", project.source.path, "-map", "0:a:0", "-vn", "-ac", "1", "-ar", "16000", "-b:a", "64k", str(audio)])
    client = OpenAI(api_key=ApiKeys.key_for(project.created_by, Provider.OPENAI), timeout=180, max_retries=1)
    with audio.open("rb") as file:
        result = client.audio.transcriptions.create(file=file, model="whisper-1", response_format="verbose_json", timestamp_granularities=["word"])
    record_usage(project.created_by, "stt", Provider.OPENAI, "whisper-1", seconds=math.ceil(project.duration))
    words, previous_end = [], 0
    for item in result.words or []:
        start, end, text = max(previous_end, float(item.start)), min(project.duration, float(item.end)), item.word.strip()
        if not text or not math.isfinite(start) or not math.isfinite(end) or end <= start:
            continue
        # Providers occasionally return a multiword token; distribute its measured interval.
        tokens = re.findall(r"\S{1,40}", text)
        for index, token in enumerate(tokens):
            words.append({"text": token, "start": round(start + (end-start)*index/len(tokens), 4), "end": round(start + (end-start)*(index+1)/len(tokens), 4)})
        previous_end = end
    if not words:
        raise ValueError("No speech was detected. Try a video with clearer spoken audio.")
    return words, preview


def project_cues(project, *, highlight=False):
    return word_cues(project.words, project.style.get("preset", "TIKTOK"), highlight=highlight)


def ass_color(value):
    return "&H00" + value[5:7] + value[3:5] + value[1:3] + "&"


def write_project_ass(project, path):
    style, unit = project.style, min(project.width, project.height)
    tiktok = style.get("preset", "TIKTOK") == "TIKTOK"
    position = style.get("position", "bottom")
    alignment = {"bottom": 2, "middle": 5, "top": 8}[position]
    margin = int(project.height * (0.22 if position == "bottom" and project.height > project.width else 0.09))
    size = unit * style.get("size", 6) / 100
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {project.width}
PlayResY: {project.height}
WrapStyle: 2
ScaledBorderAndShadow: yes
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{style.get('font', 'DejaVu Sans')},{size},{ass_color(style.get('color', '#ffffff'))},&H00FFFFFF,&H00000000,&H80000000,{-1 if tiktok else 0},0,0,0,100,100,0,0,1,{unit * 0.0045},0,{alignment},{int(project.width * 0.08)},{int(project.width * 0.14)},{margin},1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    for cue in project_cues(project, highlight=True):
        text = cue.text.replace("\\", "＼").replace("{", "｛").replace("}", "｝").replace("\r", "")
        if tiktok:
            index = -1
            def color_word(match):
                nonlocal index
                index += 1
                word = match.group().upper()
                return "{\\1c" + ass_color(style.get("highlight", "#ffe846")) + "}" + word + "{\\1c" + ass_color(style.get("color", "#ffffff")) + "}" if index == cue.active_word else word
            text = re.sub(r"\S+", color_word, text)
        # Long unbroken words still fit inside the caption area.
        longest = max(len(line) for line in cue.text.splitlines())
        scale = min(1, (20 * 6 if tiktok else 32 * 4) / style.get("size", 6) / max(1, longest))
        text = f"{{\\fs{size * scale:.2f}}}" + text.replace("\n", "\\N")
        lines.append(f"Dialogue: 0,{ass_timestamp(cue.start)},{ass_timestamp(cue.end)},Default,,0,0,0,,{text}")
    Path(path).write_text(header + "\n".join(lines) + "\n", encoding="utf-8")


def process_caption_project(project_id, token, render=False):
    queued, running = ("RENDER_QUEUED", "RENDERING") if render else ("QUEUED", "TRANSCRIBING")
    rows = CaptionProject.objects.filter(pk=project_id, job_id=token)
    if not rows.filter(status=queued).update(status=running, updated_at=timezone.now()):
        return
    project = rows.select_related("created_by").get()
    try:
        if not project.created_by.is_active:
            raise ValueError("Account is inactive.")
        with tempfile.TemporaryDirectory(prefix="captions-") as directory:
            if render:
                write_project_ass(project, Path(directory, "captions.ass"))
                output = Path(directory, "captioned.mp4")
                run_ffmpeg(["-i", project.source.path, "-map", "0:v:0", "-map", "0:a:0", "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2," + subtitles_filter("captions.ass", directory), "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart", str(output)], cwd=directory)
                with output.open("rb") as file:
                    name = project.output.storage.save(f"media/captions/{project.pk}/{token}.mp4", File(file))
                updates = {"status": "COMPLETED", "output": name}
            else:
                words, preview = transcribe_project(project, directory)
                from ..utils.timing import video_metadata

                metadata = video_metadata(preview)
                with preview.open("rb") as file:
                    name = project.preview.storage.save(f"media/captions/{project.pk}/{token}-preview.mp4", File(file))
                updates = {"status": "READY", "words": words, "preview": name, "width": metadata["width"], "height": metadata["height"]}
            if not rows.filter(status=running).update(**updates, error="", updated_at=timezone.now()):
                project.source.storage.delete(name)
    except Exception as exc:
        import logging

        logging.getLogger(__name__).exception("Caption processing failed for %s", project_id)
        message = str(exc) if isinstance(exc, ValueError) else "Could not export the video. Please retry." if render else "Could not finish processing. Check your OpenAI key or try again."
        rows.filter(status=running).update(status="READY" if project.words else "FAILED", error=message[:300], updated_at=timezone.now())
