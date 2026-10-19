"""Edit caption words independently of a scene's script and voice track."""
import hashlib
import json
import re
from pathlib import Path

from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError

from ..models import Scene
from ..utils.audio_editing import narration_enabled, narration_file
from ..utils.exceptions import VideoEditConflict
from ..utils.timing import file_timing
from .editing import changed, editable_video
from .speech_alignment import aligned_words, has_caption_alignment, narration_identity
from .subtitles import caption_style


def scene_caption_data(scene):
    duration = file_timing(narration_file(scene)).get("audio_duration")
    identity = narration_identity(scene)
    if not narration_enabled(scene) or not identity or not duration:
        raise ValidationError({"detail": "Add narration or a voiceover before editing timed captions."})
    field = narration_file(scene)
    # Generated narration can be stored with an absolute filesystem name.
    # Return its public storage URL rather than exposing that path to the player.
    relative = Path(field.path).resolve().relative_to(Path(settings.MEDIA_ROOT).resolve()).as_posix()
    audio_url = field.storage.url(relative)
    if not audio_url.startswith(("http://", "https://", "/")):
        audio_url = "/" + audio_url
    measured = has_caption_alignment(scene)
    words = aligned_words(scene) if measured else []
    if not measured:
        tokens = re.findall(r"\S{1,40}", scene.text or "")
        total, consumed = sum(len(word) for word in tokens), 0
        for token in tokens:
            start = duration * consumed / total
            consumed += len(token)
            words.append({"text": token, "start": start, "end": duration * consumed / total})
    revision = hashlib.sha256(json.dumps([identity, scene.caption_alignment], sort_keys=True).encode()).hexdigest()
    return {"words": words, "duration": duration, "revision": revision, "audio": audio_url,
            "style": caption_style(scene.video), "enabled": bool((scene.video.settings or {}).get("subtitles")),
            "timing": "edited" if measured and scene.caption_alignment.get("edited") else "measured" if measured else "estimated"}


def update_scene_captions(scene, *, words, revision):
    with editable_video(scene.video_id) as video:
        scene = get_object_or_404(Scene.objects.select_for_update(), pk=scene.pk)
        current = scene_caption_data(scene)
        if revision != current["revision"]:
            raise VideoEditConflict("The narration or captions changed. Close and reopen the caption editor before saving.")
        previous_end = 0
        for word in words:
            if word["start"] < previous_end or word["end"] > current["duration"]:
                raise ValidationError({"words": "Keep words in order, without overlaps, and within the source audio duration."})
            previous_end = word["end"]
        scene.caption_alignment = {"source": narration_identity(scene), "words": words, "edited": True}
        scene.save(update_fields=["caption_alignment"])
        changed(video, invalidate_avatar=False)
    return scene_caption_data(scene)
