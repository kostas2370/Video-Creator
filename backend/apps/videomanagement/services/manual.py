"""Create and edit projects from uploaded media, without generation jobs."""
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.db import transaction

from ..models import Music, SceneImage, UserPrompt, Video, VideoStatus, VideoType
from ..utils.audio_utils import make_scene_speech
from .audio_editing import changed, playable_voiceover
from .editing import editable_video


def create_manual_video(user, **choices):
    with transaction.atomic():
        return Video.objects.create(
            created_by=user, title=choices.pop("title"),
            prompt=UserPrompt.objects.create(prompt=""),
            video_type=VideoType.MANUAL, status=VideoStatus.READY,
            dir_name=str(Path(settings.MEDIA_ROOT, "media", "manual", uuid4().hex)),
            mode=None, settings={"narration": False, "subtitles": False,
                                 "transition_default": "CUT", **choices},
        )


def add_manual_scene(video, **choices):
    saved = None
    try:
        with editable_video(video.pk) as locked:
            scene = make_scene_speech(locked, choices.get("text", ""), False,
                                      narrate=False, position=choices.get("position"))
            if choices.get("duration") is not None:
                scene.audio_settings = {"duration": choices["duration"]}
                scene.save(update_fields=["audio_settings"])
            upload = choices.get("image")
            if upload:
                visual = SceneImage(scene=scene, with_audio=choices.get("with_audio", True))
                visual.file.save(upload.name, upload, save=False)
                saved = visual.file
                visual.save()
            changed(locked)
    except Exception:
        if saved:
            saved.storage.delete(saved.name)
        raise
    return scene


def set_music(video, upload=None):
    saved = None
    try:
        with playable_voiceover(upload) as audio, editable_video(video.pk) as locked:
            old_music = locked.music
            if audio:
                music = Music(created_by=video.created_by, name=Path(upload.name).stem[:140])
                music.file.save(audio.name, audio, save=False)
                saved = music.file
                music.save()
                locked.music = music
            else:
                locked.music = None
            locked.save(update_fields=["music"])
            changed(locked)
            if old_music and old_music.created_by_id == video.created_by_id and not old_music.video_set.exists():
                old_file = old_music.file
                old_music.delete()
                transaction.on_commit(lambda: old_file.storage.delete(old_file.name), robust=True)
    except Exception:
        if saved:
            saved.storage.delete(saved.name)
        raise
    return locked
