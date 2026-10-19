"""Edit caption words independently of a scene's script and voice track."""

import hashlib
import json
from pathlib import Path

from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError

from apps.videomanagement.exceptions import VideoEditConflict
from apps.videomanagement.models import Scene
from apps.videomanagement.services.captions.alignment import (
    caption_words,
    narration_identity,
)
from apps.videomanagement.services.scenes.editing import changed, editable_video
from apps.videomanagement.utils.audio_editing import narration_enabled, narration_file
from apps.videomanagement.utils.captions.styles import (
    caption_style,
    video_caption_style,
)
from apps.videomanagement.utils.captions.timing import (
    estimated_words,
    validate_word_bounds,
)
from apps.videomanagement.utils.timing import file_timing


def scene_caption_data(scene):
    duration = file_timing(narration_file(scene)).get("audio_duration")
    identity = narration_identity(scene)
    if not narration_enabled(scene) or not identity or not duration:
        raise ValidationError(
            {"detail": "Add narration or a voiceover before editing timed captions."}
        )
    field = narration_file(scene)
    # Generated narration can be stored with an absolute filesystem name.
    # Return its public storage URL rather than exposing that path to the player.
    relative = (
        Path(field.path)
        .resolve()
        .relative_to(Path(settings.MEDIA_ROOT).resolve())
        .as_posix()
    )
    audio_url = field.storage.url(relative)
    if not audio_url.startswith(("http://", "https://", "/")):
        audio_url = "/" + audio_url
    words = caption_words(scene)
    measured = words is not None
    if not measured:
        words = estimated_words(scene.text, duration)
    revision = hashlib.sha256(
        json.dumps([identity, scene.caption_alignment], sort_keys=True).encode()
    ).hexdigest()
    return {
        "words": words,
        "duration": duration,
        "revision": revision,
        "audio": audio_url,
        "style": caption_style(scene.video),
        "config": video_caption_style(scene.video).to_dict(),
        "enabled": bool((scene.video.settings or {}).get("subtitles")),
        "timing": "edited"
        if measured and scene.caption_alignment.get("edited")
        else "measured"
        if measured
        else "estimated",
    }


def update_scene_captions(scene, *, words, revision):
    with editable_video(scene.video_id) as video:
        scene = get_object_or_404(Scene.objects.select_for_update(), pk=scene.pk)
        current = scene_caption_data(scene)
        if revision != current["revision"]:
            raise VideoEditConflict(
                "The narration or captions changed. Close and reopen the caption editor before saving."
            )
        validate_word_bounds(words, current["duration"])
        scene.caption_alignment = {
            "source": narration_identity(scene),
            "words": words,
            "edited": True,
        }
        scene.save(update_fields=["caption_alignment"])
        changed(video, invalidate_avatar=False)
    return scene_caption_data(scene)
