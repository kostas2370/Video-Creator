import logging
import os
import uuid

from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.videomanagement.integrations.tts import ApiSyn, save
from apps.videomanagement.integrations.visuals.registry import ImageProviderRegistry
from apps.videomanagement.models import Scene, Video
from apps.videomanagement.schemas.scene_editing import SceneEditingPlanSerializer
from apps.videomanagement.services.captions.alignment import align_scene_narration
from apps.videomanagement.utils.file_utils import stored_file_exists
from apps.videomanagement.utils.prompt_utils import script_lines

from .ordering import assign_scene_positions

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

    align_scene_narration(scene)
    return scene


def make_scene_speech(
    video: Video, text: str, is_last: bool, narrate: bool = True, position: int = None
) -> Scene:
    """
    Creates a new Scene in the database and optionally narrates it using narrate_scene.
    """
    with transaction.atomic():
        Video.objects.select_for_update().get(pk=video.pk)
        active = None
        if position is not None:
            active = list(video.scenes.select_for_update())
            last = active[-1].position if active else 0
            if position < 1 or position > last + 1:
                raise ValidationError(
                    {"position": "Choose a position within the current video."}
                )
            # The picker sends the existing scene's physical position. Archived
            # rows may leave gaps, so translate it to an active-list index.
            index = next(
                (at for at, row in enumerate(active) if row.position >= position),
                len(active),
            )
        scene = Scene.objects.create(
            file=None,
            video=video,
            text=text.strip(),
            is_last=is_last,
        )
        if active is not None:
            active.insert(index, scene)
            assign_scene_positions(video, active)

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

        if not narrate:
            continue
        if stored_file_exists(scene.file):
            align_scene_narration(scene)
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

    choices = video.settings or {}
    video_provider = choices.get("ai_scene_editing") and ImageProviderRegistry.is_video(
        choices.get("provider"), user=video.created_by, mode=video.mode
    )
    for line in lines:
        if line.text not in existing:
            editing = {}
            if choices.get("ai_scene_editing") and line.editing is not None:
                plan = SceneEditingPlanSerializer(
                    data=line.editing, context={"video_provider": video_provider}
                )
                plan.is_valid(raise_exception=True)
                editing = dict(plan.validated_data)
            existing[line.text] = Scene.objects.create(
                video=video, text=line.text, is_last=line.is_last, **editing
            )

    return lines, existing


def update_scene(scene: Scene) -> Scene:
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

    return narrate_scene(scene, voice_model, dir_name, user=video.created_by)
