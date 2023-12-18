from pytube import Playlist
from ..models import Music, Scene, SceneImage
import uuid
from .bing_image_downloader import downloader
import os
from openai import OpenAI
import requests
from django.conf import settings
from pytube import YouTube


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


def generate_from_dalle(prompt, dir_name, style):

    client = OpenAI(api_key=settings.OPEN_API_KEY)

    response = client.images.generate(
      model="dall-e-3",
      prompt= prompt,
      size="1792x1024",
      quality="standard",
      n=1,
      style = style
    )

    image_url = response.data[0].url
    response = requests.get(image_url)
    x = str(uuid.uuid4())
    open(rf"{dir_name}/images/{x}.png", "wb").write(response.content)

    return rf"{dir_name}/images/{x}.png"


def create_image_scene(prompt, image, text, dir_name , mode="webscrap", style=""):
    scene = Scene.objects.get(prompt = prompt, text = text.strip())

    if mode=="AI":
        downloaded_image = generate_from_dalle(image, dir_name, style = style)

    else:
        downloaded_image = download_image(image, f'{dir_name}/images/', amount = 6)
        downloaded_image = check_which_file_exists(downloaded_image)
    if downloaded_image is not None and len(downloaded_image) > 0:
        SceneImage.objects.create(scene = scene, file = downloaded_image)


def create_image_scenes(video, mode="webscrap", style="natural"):
    dir_name = video.dir_name
    for j in video.gpt_answer['scenes']:
        if video.prompt.template.is_sentenced:
            for x in j['dialogue']:
                create_image_scene(video.prompt, x['image'], x['sentence'], dir_name, mode=mode,  style=style)

        else:
            create_image_scene(video.prompt, j['image'], j['dialogue'], dir_name, mode=mode, style=style)


def download_video(url, dir_name):
    yt = YouTube(url)
    video = yt.streams.get_highest_resolution()
    video.download(dir_name)
    return rf'{dir_name}{yt.title}.mp4'
