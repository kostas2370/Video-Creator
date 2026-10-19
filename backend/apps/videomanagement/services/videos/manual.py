"""Create and edit projects from uploaded media, without generation jobs."""

from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.db import transaction

from apps.videomanagement.models import (
    SceneImage,
    TransitionStyle,
    UserPrompt,
    Video,
    VideoStatus,
    VideoType,
)
from apps.videomanagement.services.scenes.editing import changed, editable_video
from apps.videomanagement.services.scenes.narration import make_scene_speech


def create_manual_video(user, **choices):
    with transaction.atomic():
        return Video.objects.create(
            created_by=user,
            title=choices.pop("title"),
            prompt=UserPrompt.objects.create(prompt=""),
            video_type=VideoType.MANUAL,
            status=VideoStatus.READY,
            dir_name=str(Path(settings.MEDIA_ROOT, "media", "manual", uuid4().hex)),
            mode=None,
            settings={
                "narration": False,
                "subtitles": False,
                "transition_default": TransitionStyle.CUT,
                **choices,
            },
        )


def add_manual_scene(
    video, *, text="", image=None, duration=None, position=None, with_audio=True
):
    visual = None
    try:
        with editable_video(video.pk) as locked:
            scene = make_scene_speech(
                locked, text, False, narrate=False, position=position
            )
            if duration is not None:
                scene.audio_settings = {"duration": duration}
                scene.save(update_fields=["audio_settings"])
            if image:
                visual = SceneImage(scene=scene, file=image, with_audio=with_audio)
                visual.save()
            changed(locked)
    except Exception:
        # Database rollback does not remove files already written to storage.
        if visual and visual.file._committed:
            visual.file.delete(save=False)
        raise
    return scene
