import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path

from django.core.files import File
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError

from apps.videomanagement.models import Scene
from apps.videomanagement.services.scenes.editing import changed, editable_video
from apps.videomanagement.utils.audio_editing import (
    duration_override,
    narration_file,
    waveform,
)
from apps.videomanagement.utils.timing import file_timing, media_timing


def update_audio(scene, changes):
    with editable_video(scene.video_id) as video:
        scene = get_object_or_404(Scene.objects.select_for_update(), pk=scene.pk)
        choices = {**scene.audio_settings, **changes}
        duration = file_timing(narration_file(scene)).get("audio_duration")
        start, end = choices.get("trim_start", 0), choices.get("trim_end")
        if end is not None and end <= start:
            raise ValidationError({"trim_end": "Trim end must be after trim start."})
        if duration is not None and (
            start >= duration or (end is not None and end > duration + 0.02)
        ):
            raise ValidationError(
                {"trim_start": "The trim must stay within the audio file."}
            )
        scene.audio_settings = choices
        scene.save(update_fields=["audio_settings"])
        changed(video)
    return scene


@contextmanager
def playable_voiceover(upload):
    # Inspect the actual stream rather than trusting extension or content type.
    if upload is None:
        yield None
        return
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory, "source.audio")
        with source.open("wb") as temporary:
            for chunk in upload.chunks():
                temporary.write(chunk)
        duration = media_timing(source).get("audio_duration")
        if duration is not None:
            if duration > 900:
                raise ValidationError(
                    {"file": "Upload playable audio up to 15 minutes long."}
                )
            upload.seek(0)
            yield upload
            return
        # MediaRecorder WebM files often have no duration header. Decode them
        # into a seekable WAV so validation, preview and rendering share timing.
        normalized = Path(directory, "voiceover.wav")
        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-nostdin",
                    "-y",
                    "-i",
                    str(source),
                    "-map",
                    "0:a:0",
                    "-t",
                    "901",
                    "-ac",
                    "1",
                    "-ar",
                    "48000",
                    "-c:a",
                    "pcm_s16le",
                    str(normalized),
                ],
                capture_output=True,
                timeout=60,
                check=True,
            )
        except (OSError, subprocess.SubprocessError):
            raise ValidationError(
                {
                    "file": "Could not read this recording. Try recording again or upload an audio file."
                }
            )
        duration = media_timing(normalized).get("audio_duration")
        if duration is None or duration > 900:
            raise ValidationError(
                {"file": "Upload playable audio up to 15 minutes long."}
            )
        with normalized.open("rb") as audio:
            yield File(audio, name=f"{Path(upload.name).stem}.wav")


def save_voiceover(scene, upload=None):
    with playable_voiceover(upload) as prepared:
        return store_voiceover(scene, prepared)


def store_voiceover(scene, upload):
    saved_name = None
    storage = scene.voiceover.storage
    try:
        with editable_video(scene.video_id) as video:
            scene = get_object_or_404(Scene.objects.select_for_update(), pk=scene.pk)
            old_name = scene.voiceover.name
            if upload is None:
                scene.voiceover = ""
            else:
                scene.voiceover.save(upload.name, upload, save=False)
                saved_name = scene.voiceover.name
            override = duration_override(scene)
            scene.audio_settings = (
                {"duration": override} if override is not None else {}
            )
            scene.save(update_fields=["voiceover", "audio_settings"])
            changed(video)
            if old_name:
                transaction.on_commit(lambda: storage.delete(old_name), robust=True)
    except Exception:
        if saved_name:
            storage.delete(saved_name)
        raise
    return scene


def audio_waveform(scene):
    field = narration_file(scene)
    if not field:
        raise ValidationError({"detail": "This scene has no voice audio yet."})
    try:
        return waveform(field.path)
    except (OSError, ValueError, subprocess.SubprocessError):
        raise ValidationError(
            {"detail": "Could not read this audio. Try another file."}
        )
