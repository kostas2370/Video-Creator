import os
from random import randint
from ..models import Music, Backgrounds, Avatars, VoiceModels


def generate_directory(name, x=0):

    while True:
        dir_name = (name + (' ' + str(x) if x is not 0 else '')).strip()
        if not os.path.exists(dir_name):
            os.mkdir(dir_name)
            os.mkdir(rf'{dir_name}\dialogues')
            os.mkdir(rf'{dir_name}\images')

            return dir_name
        else:
            x += 1


def select_music(category=None):
    if category is None:
        raise Exception('You need to add a category')

    music = Music.objects.filter(category = category)

    if music.count() > 0:
        return music[randint(0, music.count() - 1)]

    return None


def select_background(category=None):
    if category is None:
        raise Exception('You need to add a category')

    back = Backgrounds.objects.filter(category = category)
    return back[randint(0, back.count() - 1)]


def select_avatar(selected='random', voice_model=None):
    if selected == 'random':
        if voice_model is None:
            avatars = Avatars.objects.all()
        else:
            avatars = Avatars.objects.filter(voice = voice_model)

        return avatars[randint(0, avatars.count()-1)]

    if type(selected) == int:
        items = Avatars.objects.filter(id = selected)
        if items.count() == 1:
            return items.first()

    return None


def select_voice():
    voice = VoiceModels.objects.all()
    return voice[randint(0, voice.count() - 1)]
