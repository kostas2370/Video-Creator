import uuid

from .tts_utils import save, ApiSyn
from ..models import Scene, Video
import os


def make_scene_speech(voice_model, dir_name, prompt, text, is_last) -> Scene:
    filename = str(uuid.uuid4())
    syn = ApiSyn(provider=voice_model.provider, path=voice_model.path)
    sound = save(syn, text, save_path=f"{dir_name}/dialogues/{filename}.wav")
    scene = Scene.objects.create(
        file=sound, prompt=prompt, text=text.strip(), is_last=is_last
    )
    return scene


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
    for scene in video.gpt_answer["scenes"]:
        sentences = scene["sentences"]
        for index, sentence in enumerate(sentences):
            make_scene_speech(
                voice_model,
                video.dir_name,
                video.prompt,
                sentence["sentence"],
                index == len(sentences) - 1,
            )


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

    sound = save(syn, scene.text, save_path=f"{dir_name}/dialogues/{filename}.wav")
    scene.file = sound
    scene.save()
