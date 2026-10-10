import logging
import os
import uuid
from typing import Optional

from django.db import transaction
from django.db.models import Max
from rest_framework.exceptions import ValidationError

from .file_utils import stored_file_exists
from .prompt_utils import script_lines
from .tts_utils import ApiSyn, save
from ..models import Scene, Video

logger = logging.getLogger(__name__)


def narrate_scene(scene: Scene, voice_model, dir_name: str, user=None) -> Scene:
    """
    Narrates an existing scene and updates its file path in the database.
    Supports both standard API providers and user custom providers.
    """
    if not voice_model:
        return scene

    syn = ApiSyn(
        provider=voice_model.provider,
        path=voice_model.path,
    )

    filename = str(uuid.uuid4())
    save_path = os.path.join(dir_name, "dialogues", f"{filename}.wav")

    scene.file = save(
        syn,
        scene.text,
        save_path=save_path,
        user=user,
    )
    scene.save()

    return scene


def make_scene_speech(
    video: Video, text: str, is_last: bool, narrate: bool = True, position: int = None
) -> Scene:
    """
    Creates a new Scene in the database and optionally narrates it using narrate_scene.
    """
    with transaction.atomic():
        Video.objects.select_for_update().get(pk=video.pk)
        if position is not None:
            last = video.scenes.aggregate(last=Max("position"))["last"] or 0
            if position < 1 or position > last + 1:
                raise ValidationError({"position": "Choose a position within the current video."})
            # Move from the end so each destination is free under the unique constraint.
            for existing in video.scenes.filter(position__gte=position).order_by("-position"):
                Scene.objects.filter(pk=existing.pk).update(position=existing.position + 1)
        scene = Scene.objects.create(
            file=None, video=video, text=text.strip(), is_last=is_last, position=position
        )

    if narrate and video.voice_model:
        try:
            narrate_scene(
                scene, video.voice_model, video.dir_name, user=video.created_by
            )
        except Exception:
            logger.exception("Could not narrate newly created scene %s", scene.pk)

    return scene


def make_scenes_speech(video: Video) -> None:
    """
    Generate speech audio files for scenes based on the provided video script.
    """
    voice_model = video.voice_model
    narrate = (video.settings or {}).get("narration", True)

    lines, existing = ensure_scene_rows(video)

    for line in lines:
        scene = existing[line.text]

        if not narrate or stored_file_exists(scene.file):
            continue

        try:
            narrate_scene(scene, voice_model, video.dir_name, user=video.created_by)
        except Exception:
            logger.exception("Could not narrate scene %s", scene.pk)


def ensure_scene_rows(video: Video):
    """Create script scene rows before audio and visual work can run concurrently."""
    lines = list(script_lines(video.gpt_answer))
    script_texts = {line.text for line in lines}
    existing = {scene.text: scene for scene in video.scenes.all()}

    video.scenes.exclude(text__in=script_texts).delete()

    for line in lines:
        if line.text not in existing:
            existing[line.text] = Scene.objects.create(
                video=video, text=line.text, is_last=line.is_last
            )

    return lines, existing


def update_scene(scene: Scene) -> Optional[Scene]:
    """
    Update the speech audio file for a given scene.
    Removes cached avatar video output if it exists and regenerates audio.
    """
    video = scene.video
    dir_name = video.dir_name
    voice_model = video.voice_model

    avatar_video = os.path.join(os.getcwd(), dir_name, "output_avatar.mp4")
    if video.avatar and os.path.exists(avatar_video):
        try:
            os.remove(avatar_video)
        except OSError:
            logger.exception("Failed to remove cached avatar video at %s", avatar_video)

    try:
        return narrate_scene(scene, voice_model, dir_name, user=video.created_by)
    except Exception:
        logger.exception("Could not update narration for scene %s", scene.pk)
        return None
