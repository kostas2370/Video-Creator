"""Persist measured word timing outside preview and subtitle download requests."""

import hashlib
import logging
import tempfile
from pathlib import Path

from django.conf import settings

from apps.apikeysmanagement.models import ApiKeys, Provider
from apps.videomanagement.services.captions.transcription import transcribe_audio
from apps.videomanagement.utils.audio_editing import narration_enabled, narration_file
from apps.videomanagement.utils.timing import file_timing

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
    return bool(
        alignment.get("source") and alignment["source"] == narration_identity(scene)
    )


def caption_words(scene):
    """None means no valid alignment; an empty list means captions were cleared."""
    return (
        scene.caption_alignment.get("words", [])
        if has_caption_alignment(scene)
        else None
    )


def aligned_words(scene):
    return caption_words(scene) or []


def align_scene_narration(scene):
    """Best effort transcription; never make a successful voice job fail on captions."""
    if not (scene.video.settings or {}).get("subtitles") or not narration_enabled(
        scene
    ):
        return
    identity = narration_identity(scene)
    if not identity or has_caption_alignment(scene):
        return
    try:
        key = None
        if settings.SPEECH_TRANSCRIPTION_PROVIDER == "openai":
            key = ApiKeys.key_for(scene.video.created_by, Provider.OPENAI)
            if not key:
                return
        duration = file_timing(narration_file(scene)).get("audio_duration")
        if not duration:
            return
        with tempfile.TemporaryDirectory(prefix="narration-captions-") as directory:
            words = transcribe_audio(
                narration_file(scene).path,
                scene.video.created_by,
                duration,
                directory,
                api_key=key,
            )
        if words and narration_identity(scene) == identity:
            alignment = {"source": identity, "words": words}
            # Do not overwrite other edits with the worker's scene instance.
            type(scene).objects.filter(pk=scene.pk).update(caption_alignment=alignment)
            scene.caption_alignment = alignment
    except Exception:
        logger.exception(
            "Could not align narration captions for scene %s; using estimated timing",
            scene.pk,
        )
