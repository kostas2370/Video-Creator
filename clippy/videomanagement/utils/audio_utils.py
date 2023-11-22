from .tts_utils import create_model, save
from ..models import Speech
import uuid


def make_scenes_speech(gpt_answer, video, voice_model, dir_name):

    syn = create_model(model = voice_model.path)
    sounds = []
    for j in gpt_answer["scenes"]:
        filename = str(uuid.uuid4())
        sound = save(syn, j['dialogue']["dialogue"], save_path = f'{dir_name}/dialogues/{filename}.wav')
        Speech.objects.create(file = sound, prompt = video.prompt, text = j['dialogue']["dialogue"].strip())
        sounds.append(sound)

    return sounds
