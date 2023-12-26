from .tts_utils import create_model, save
from ..models import Scene, Videos
import uuid


def make_scenes_speech(video):
    dir_name = video.dir_name
    voice_model = video.voice_model
    syn = voice_model.path
    gpt_answer = video.gpt_answer
    is_sentenced = True if video.prompt.template is None else video.prompt.template.is_sentenced
    if voice_model.type == 'Local' or voice_model.type == "LOCAL":
        syn = create_model(model = syn)

    for j in gpt_answer["scenes"]:
        if is_sentenced:
            for index, sentence in enumerate(j['dialogue']):
                filename = str(uuid.uuid4())

                sound = save(syn, sentence['sentence'], save_path = f'{dir_name}/dialogues/{filename}.wav')
                Scene.objects.create(file = sound, prompt = video.prompt, text = sentence['sentence'].strip(),
                                     is_last = index == len(j['dialogue']) - 1)

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

    filename = str(uuid.uuid4())

    sound = save(syn, scene.text, save_path = f'{dir_name}/dialogues/{filename}.wav')
    scene.file = sound
    scene.save()

    return True
