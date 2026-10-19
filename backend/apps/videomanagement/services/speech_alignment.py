"""Persist measured word timing outside preview and subtitle download requests."""
import hashlib
import logging
import math
import re
import subprocess
import tempfile
from pathlib import Path

from openai import OpenAI

from apps.apikeysmanagement.models import ApiKeys, Provider
from ..utils.audio_editing import narration_enabled, narration_file
from ..utils.timing import file_timing
from ..utils.usage import record_usage

logger = logging.getLogger(__name__)


def narration_identity(scene):
    field = narration_file(scene)
    if not field:
        return None
    try:
        path = Path(field.path)
        stat = path.stat()
        identity = f"{path}:{stat.st_size}:{stat.st_mtime_ns}:{scene.text}"
        return hashlib.sha256(identity.encode()).hexdigest()
    except (OSError, ValueError):
        return None


def has_caption_alignment(scene):
    alignment = getattr(scene, "caption_alignment", None) or {}
    return bool(alignment.get("source") and alignment["source"] == narration_identity(scene))


def aligned_words(scene):
    return scene.caption_alignment.get("words", []) if has_caption_alignment(scene) else []


def align_scene_narration(scene):
    """Best effort transcription; never make a successful voice job fail on captions."""
    if not (scene.video.settings or {}).get("subtitles") or not narration_enabled(scene):
        return
    identity = narration_identity(scene)
    if not identity or has_caption_alignment(scene):
        return
    try:
        key = ApiKeys.key_for(scene.video.created_by, Provider.OPENAI)
        if not key:
            return
        duration = file_timing(narration_file(scene)).get("audio_duration")
        if not duration:
            return
        with tempfile.TemporaryDirectory(prefix="narration-captions-") as directory:
            audio = Path(directory, "speech.mp3")
            subprocess.run(
                ["ffmpeg", "-v", "error", "-nostdin", "-y", "-i", narration_file(scene).path,
                 "-vn", "-ac", "1", "-ar", "16000", "-b:a", "64k", str(audio)],
                capture_output=True, check=True, timeout=120,
            )
            client = OpenAI(api_key=key, timeout=180, max_retries=1)
            with audio.open("rb") as file:
                result = client.audio.transcriptions.create(
                    file=file, model="whisper-1", response_format="verbose_json",
                    timestamp_granularities=["word"],
                )
            record_usage(scene.video.created_by, "stt", Provider.OPENAI, "whisper-1", seconds=math.ceil(duration))
        words, previous_end = [], 0
        for item in result.words or []:
            start, end = float(item.start), float(item.end)
            if not math.isfinite(start) or not math.isfinite(end):
                continue
            start, end = max(previous_end, 0, start), min(duration, end)
            tokens = re.findall(r"\S{1,40}", item.word.strip())
            if not tokens or end <= start:
                continue
            for index, token in enumerate(tokens):
                words.append({"text": token, "start": start + (end-start)*index/len(tokens),
                              "end": start + (end-start)*(index+1)/len(tokens)})
            previous_end = end
        if words and narration_identity(scene) == identity:
            alignment = {"source": identity, "words": words}
            # Do not overwrite other edits with the worker's scene instance.
            type(scene).objects.filter(pk=scene.pk).update(caption_alignment=alignment)
            scene.caption_alignment = alignment
    except Exception:
        logger.exception("Could not align narration captions for scene %s; using estimated timing", scene.pk)
