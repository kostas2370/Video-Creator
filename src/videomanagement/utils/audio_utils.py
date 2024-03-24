from .tts_utils import create_model, save, ApiSyn
from ..models import Scene, Videos
import uuid


def make_scenes_speech(video):
    dir_name = video.dir_name
    voice_model = video.voice_model
    syn = voice_model.path
    gpt_answer = video.gpt_answer
    search_field = "scene" if "scene" in gpt_answer["scenes"][0] and isinstance(gpt_answer["scenes"][0]["scene"], list)\
                   else "sections" if "sections" in gpt_answer["scenes"][0] else "sentence"

    is_sentenced = True if video.prompt.template is None else video.prompt.template.is_sentenced
    if voice_model.type.lower() == 'local':
        syn = create_model(model = syn)
    elif voice_model.type.lower() == 'api':
        syn = ApiSyn(provider = syn.provider, path = video.voice_model.path)

    for j in gpt_answer["scenes"]:
        if is_sentenced:
            for index, sentence in enumerate(j[search_field]):
                filename = str(uuid.uuid4())

                sound = save(syn, sentence['narration'], save_path = f'{dir_name}/dialogues/{filename}.wav')
                Scene.objects.create(file = sound, prompt = video.prompt, text = sentence['narration'].strip(),
                                     is_last = index == len(j[search_field]) - 1)

        else:
            filename = str(uuid.uuid4())
            sound = save(syn, j['dialogue'], save_path = f'{dir_name}/dialogues/{filename}.wav')
            Scene.objects.create(file = sound, prompt = video.prompt, text = j['dialogue'].strip())

    return True


def update_scene(scene):
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

    return True
