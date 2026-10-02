import logging
import os
import uuid
from typing import Union

from .prompt_utils import script_lines
from .file_utils import stored_file_exists
from .tts_utils import (
    ApiSyn,
    tts_from_open_api,
    tts_from_eleven_labs,
    tts_from_60db,
    tts_from_custom_provider,
)
from ..models import Scene, Video, VoiceModelType


logger = logging.getLogger(__name__)


def save(
    syn: Union[ApiSyn, None], text: str = "", save_path: str = "", user=None
) -> Union[str, None]:
    if not syn:
        return None

    if syn.provider == "open_ai":
        tts_from_open_api(text, save_path, syn.path, user=user)
    elif syn.provider == "eleven_labs":
        tts_from_eleven_labs(text, save_path, syn.path, user=user)
    elif syn.provider == "60db":
        tts_from_60db(text, save_path, syn.path, user=user)
    else:
        provider_name = syn.custom_provider_name or syn.provider
        tts_from_custom_provider(
            text, save_path, syn.path, user=user, custom_provider_name=provider_name
        )

    if not os.path.exists(save_path):
        logger.error("%s wrote no audio for %r", syn.provider, save_path)
        return None

    return save_path


def has_narration(scene: Scene) -> bool:
    return stored_file_exists(scene.file)


def narrate_scene(scene: Scene, voice_model, dir_name, user=None) -> Scene:
    """
    Narrates an existing scene and updates its file path in the database.
    Supports both standard API providers and user custom providers.
    """
    if not voice_model:
        return scene

    syn = ApiSyn(
        provider=voice_model.provider,
        path=voice_model.path,
        custom_provider_name=voice_model.provider if voice_model.type == VoiceModelType.CUSTOM_API else None,
    )

    filename = str(uuid.uuid4())
    scene.file = save(
        syn,
        scene.text,
        save_path=f"{dir_name}/dialogues/{filename}.wav",
        user=user,
    )
    scene.save()

    return scene


def make_scene_speech(video: Video, text: str, is_last: bool, narrate: bool = True) -> Scene:
    """
    Creates a new Scene in the database and optionally narrate it using narrate_scene.
    """
    scene = Scene.objects.create(
        file=None, video=video, text=text.strip(), is_last=is_last
    )

    if narrate and video.voice_model:
        narrate_scene(scene, video.voice_model, video.dir_name, user=video.created_by)

    return scene


def make_scenes_speech(video: Video) -> None:
    """
    Generate speech audio files for scenes based on the provided video.

    Parameters:
    -----------
    video : Video
        The video object containing information about the scenes and speech generation settings.

    Returns:
    --------
    None
    """
    voice_model = video.voice_model
    narrate = (video.settings or {}).get("narration", True)
    existing = {scene.text: scene for scene in video.scenes.all()}

    for line in script_lines(video.gpt_answer):
        scene = existing.get(line.text) or Scene.objects.create(
            video=video, text=line.text, is_last=line.is_last
        )

        if not narrate or has_narration(scene):
            continue

        try:
            narrate_scene(scene, voice_model, video.dir_name, user=video.created_by)
        except Exception:
            logger.exception("Could not narrate scene %s", scene.pk)


def update_scene(scene: Scene) -> None:
    """
    Update the speech audio file for a given scene.
    Removes cached avatar video output if it exists and regenerates audio.
    """
    video = scene.video
    dir_name = video.dir_name
    voice_model = video.voice_model

    avatar_video = os.path.join(os.getcwd(), video.dir_name, "output_avatar.mp4")
    if video.avatar and os.path.exists(avatar_video):
        os.remove(avatar_video)

    narrate_scene(scene, voice_model, dir_name, user=video.created_by)