import logging
import tempfile
from pathlib import Path

from django.core.files import File
from django.db import transaction
from django.utils.text import slugify
from rest_framework.exceptions import ValidationError

from apps.common.youtube import SourceImportError, download_youtube_video
from apps.videomanagement.models import Music
from apps.videomanagement.services.scenes.audio import playable_voiceover
from apps.videomanagement.services.scenes.editing import changed, editable_video


def set_music(video, upload=None):
    saved = None
    try:
        with playable_voiceover(upload) as audio, editable_video(video.pk) as locked:
            old_music = locked.music
            if audio:
                music = Music(
                    created_by=video.created_by, name=Path(upload.name).stem[:140]
                )
                music.file.save(audio.name, audio, save=False)
                saved = music.file
                music.save()
                locked.music = music
            else:
                locked.music = None
            locked.save(update_fields=["music"])
            changed(locked)
            if (
                old_music
                and old_music.created_by_id == video.created_by_id
                and not old_music.video_set.exists()
            ):
                old_file = old_music.file
                old_music.delete()
                transaction.on_commit(
                    lambda: old_file.storage.delete(old_file.name), robust=True
                )
    except Exception:
        if saved:
            saved.storage.delete(saved.name)
        raise
    return locked


def set_music_from_youtube(video, url):
    # Check before downloading; set_music checks again when storing the result.
    with editable_video(video.pk):
        pass
    with tempfile.TemporaryDirectory() as directory:
        try:
            path, title = download_youtube_video(
                url,
                directory,
                audio_only=True,
                max_duration=900,
                max_bytes=50 * 1024 * 1024,
            )
        except SourceImportError as exc:
            raise ValidationError({"youtube_url": str(exc)}) from exc
        except Exception as exc:
            logging.getLogger(__name__).exception("YouTube music import failed")
            raise ValidationError(
                {
                    "youtube_url": "Could not download this YouTube audio. Try another link or upload a file."
                }
            ) from exc
        with path.open("rb") as audio:
            name = slugify(title)[:100] or "youtube-music"
            return set_music(video, File(audio, name=f"{name}{path.suffix}"))
