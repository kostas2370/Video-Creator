from pytube import Playlist
from ..models import Music, Scene, SceneImage
import os
import uuid
from bing_image_downloader import downloader
import os


def download_playlist(url, category):
    playlist = Playlist(url)
    for music in playlist.videos:
        stream = music.streams.filter(only_audio = True).first()
        try:

            filename = str(uuid.uuid4())
            song = stream.download('media/music')
            new_file = f'media/music/{filename}.mp3'
            os.rename(song, new_file)

            Music.objects.create(name = stream.title, file = new_file, category = category)

        except:
            pass

    return True


def download_image(query, path, amount=1):
    return downloader.download(query = f'{query} hd', limit = amount, output_dir = path, adult_filter_off = True,
                               force_replace = False, timeout = 60, )


def check_which_file_exists(images):
    for i in images:
        if os.path.exists(i):
            return i
    return None


def create_image_scene(prompt, image, text, dir_name):
    scene = Scene.objects.get(prompt = prompt, text = text.strip())
    downloaded_image = download_image(image, f'{dir_name}/images/', amount = 6)
    if len(downloaded_image) > 0:
        SceneImage.objects.create(scene = scene, file = check_which_file_exists(downloaded_image))


def create_image_scenes(video):
    dir_name = video.dir_name
    for j in video.gpt_answer['scenes']:
        if video.prompt.template.is_sentenced:
            for x in j['dialogue']:
                create_image_scene(video.prompt, x['image'], x['sentence'], dir_name)

        else:
            create_image_scene(video.prompt, j['image'], j['dialogue'], dir_name)
