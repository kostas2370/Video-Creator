import uuid

from .tts_utils import save, ApiSyn, create_model
from ..models import Scene, Videos


def make_scenes_speech(video: Videos) -> None:
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
    - The speech synthesis can be performed using either a local model or an API, depending on the settings in the video object.
    - Each scene's dialogue or narration text is converted to speech and saved as a WAV file in the video's directory.
    """

    dir_name = video.dir_name
    voice_model = video.voice_model
    syn = voice_model.path
    gpt_answer = video.gpt_answer
    first_scene = gpt_answer["scenes"][0]
    search_field = "scene" if "scene" in first_scene and isinstance(first_scene["scene"], list)\
                   else "sections" if "sections" in first_scene else "sentences"

    narration_field = "sentence" if "sentence" in first_scene[search_field][0] else "narration"
    is_sentenced = True if video.prompt.template is None else video.prompt.template.is_sentenced
    if voice_model.type.lower() == 'local':
        syn = create_model(model = syn)
    elif voice_model.type.lower() == 'api':
        syn = ApiSyn(provider =video.voice_model.provider, path = video.voice_model.path)

    for j in gpt_answer["scenes"]:
        if is_sentenced:
            for index, sentence in enumerate(j[search_field]):
                filename = str(uuid.uuid4())

                sound = save(syn, sentence[narration_field], save_path = f'{dir_name}/dialogues/{filename}.wav')
                Scene.objects.create(file = sound, prompt = video.prompt, text = sentence[narration_field].strip(),
                                     is_last = index == len(j[search_field]) - 1)

        else:
            filename = str(uuid.uuid4())
            sound = save(syn, j['dialogue'], save_path = f'{dir_name}/dialogues/{filename}.wav')
            Scene.objects.create(file = sound, prompt = video.prompt, text = j['dialogue'].strip())

    return


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
    video = Videos.objects.get(prompt__id=scene.prompt.id)
    dir_name = video.dir_name
    voice_model = video.voice_model
    syn = voice_model.path
    if voice_model.type == 'Local' or voice_model.type == "LOCAL":
        syn = create_model(model = syn)

    elif voice_model.type.lower() == 'api':
        syn = ApiSyn(provider = video.voice_model.provider, path = video.voice_model.path)

    filename = str(uuid.uuid4())

    sound = save(syn, scene.text, save_path = f'{dir_name}/dialogues/{filename}.wav')
    scene.file = sound
    scene.save()
