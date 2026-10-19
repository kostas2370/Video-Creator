from pathlib import Path

from django.db import transaction

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
