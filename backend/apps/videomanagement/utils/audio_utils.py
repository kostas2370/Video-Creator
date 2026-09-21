import logging
import os
import uuid

from .prompt_utils import scene_text
from .file_utils import stored_file_exists
from .tts_utils import save, ApiSyn
from ..models import Scene, Video


logger = logging.getLogger(__name__)


def has_narration(scene: Scene) -> bool:
    return stored_file_exists(scene.file)


def narrate_scene(scene: Scene, voice_model, dir_name, user=None) -> Scene:
    syn = ApiSyn(provider=voice_model.provider, path=voice_model.path)
    scene.file = save(
        syn,
        scene.text,
        save_path=f"{dir_name}/dialogues/{uuid.uuid4()}.wav",
        user=user,
    )
    scene.save()

    return scene


def make_scene_speech(
    voice_model, dir_name, prompt, text, is_last, narrate=True, user=None
) -> Scene:
    sound = None
    if narrate:
        filename = str(uuid.uuid4())
        syn = ApiSyn(provider=voice_model.provider, path=voice_model.path)
        sound = save(
            syn, text, save_path=f"{dir_name}/dialogues/{filename}.wav", user=user
        )

    return Scene.objects.create(
        file=sound, prompt=prompt, text=text.strip(), is_last=is_last
    )


def make_scenes_speech(video: Video) -> None:
    """
    Generate speech audio files for scenes based on the provided video.

    Parameters:
    -----------
    video : Videos
        The video object containing information about the scenes and speech generation settings.

    Returns:
    --------
    None

    Notes:
    ------
    - This function generates speech audio files for each scene in the video based on the provided GPT-3.5 answer.
    - The speech synthesis can be performed using either a local model or an API, depending on the settings in
      the video object.
    - Each scene's dialogue or narration text is converted to speech and saved as a WAV file in the video's directory.
    """

    voice_model = video.voice_model
    narrate = video.settings.get("narration", True)
    existing = {s.text: s for s in video.prompt.scenes.all()}

    for scene in video.gpt_answer["scenes"]:
        sentences = scene["sentences"]
        for index, sentence in enumerate(sentences):
            text = scene_text(sentence)
            is_last = index == len(sentences) - 1
            line = existing.get(text.strip())

            if line is None:
                try:
                    make_scene_speech(
                        voice_model,
                        video.dir_name,
                        video.prompt,
                        text,
                        is_last,
                        narrate=narrate,
                        user=video.created_by,
                    )
                except Exception:
                    logger.exception("Could not narrate %r", text[:40])
                    Scene.objects.create(
                        prompt=video.prompt, text=text.strip(), is_last=is_last
                    )
                continue

            if not narrate or has_narration(line):
                continue

            try:
                narrate_scene(line, voice_model, video.dir_name, user=video.created_by)
            except Exception:
                logger.exception("Could not narrate scene %s", line.pk)


def update_scene(scene: Scene) -> None:
    """
    Update the speech audio file for a given scene.

    Parameters:
    -----------
    scene : Scene
        The scene object to be updated.

    Returns:
    --------
    None

    Notes:
    ------
    - This function updates the speech audio file for the provided scene.
    - It retrieves the associated video and voice model information to perform the speech synthesis.
    - The updated audio file is saved in the scene's directory.
    """
    video = Video.objects.get(prompt__id=scene.prompt.id)
    dir_name = video.dir_name
    voice_model = video.voice_model

    if video.avatar and os.path.exists(
        rf"{os.getcwd()}\{video.dir_name}\output_avatar.mp4"
    ):
        os.remove(rf"{os.getcwd()}\{video.dir_name}\output_avatar.mp4")

    syn = ApiSyn(provider=voice_model.provider, path=voice_model.path)

    filename = str(uuid.uuid4())

    sound = save(
        syn,
        scene.text,
        save_path=f"{dir_name}/dialogues/{filename}.wav",
        user=video.created_by,
    )
    scene.file = sound
    scene.save()
