from pytube import Playlist
from ..models import Music, Scene, SceneImage, Videos
import uuid
from .bing_image_downloader import downloader
import os
from openai import OpenAI
import requests
from django.conf import settings
from pytube import YouTube
from .exceptions import FileNotDownloadedError
from .prompt_utils import format_dalle_prompt
from .google_image_downloader import downloader as google_downloader
from .video_utils import split_video_and_mp3, add_text_to_video
import logging
import json
import sys
import urllib.request
from .mapper import modes, default_providers


logger = logging.getLogger(__name__)

thismodule = sys.modules[__name__]


def download_playlist(url: str, category: str) -> None:
    playlist = Playlist(url)
    for music in playlist.videos:
        stream = music.streams.filter(only_audio = True).first()
        try:

            filename = str(uuid.uuid4())
            song = stream.download('media/music')
            new_file = f'media/music/{filename}.mp3'
            if not os.path.isfile(song):
                raise FileNotDownloadedError()

            os.rename(song, new_file)

            Music.objects.create(name = stream.title, file = new_file, category = category)

        except FileNotDownloadedError:
            logger.error("Error downloading song")


def download_image(query: str, path: str, amount: int = 1, *args, **kwargs) -> list[str]:
    try:
        logger.info("Downloading image from bing")
        return downloader.download(query = f'{query}', limit = amount, output_dir = path,
                                   adult_filter_off = True,
                                   force_replace = False, timeout = 60, filter = 'photo')[0]

    except Exception as exc:
        logger.error(f"Error downloading image with query {query} Error {exc}")


def download_image_from_google(q: str, path: str, amt: int = 1, *args, **kwargs) -> str:
    try:
        logger.info("Downloading image from google")
        return google_downloader.download(q = q, path = path, amt = amt)

    except Exception as exc:
        logger.error(f"Error downloading image with query {q} Error {exc}")


def download_video(url: str, dir_name: str) -> str:
    yt = YouTube(url)
    video = yt.streams.get_highest_resolution()
    video.download(dir_name)
    return rf'{dir_name}{yt.title}.mp4'


def download_music(url: str) -> str:
    if url is None:
        return None

    yt = YouTube(url)

    video = yt.streams.filter(only_audio = True).first()
    existing = Music.objects.filter(name= video.title)
    if existing.count() > 0:
        return existing.first()

    video = video.download('media/music')
    filename = str(uuid.uuid4())
    new_file = f'media/music/{filename}.mp3'
    os.rename(video, new_file)
    mus = Music.objects.create(name = yt.title, file = new_file, category = "ΟΤΗΕR")
    return mus


def generate_from_dalle(prompt: str, dir_name: str, style: str, title: str = "") -> str:
    logger.warning("API CALL IN DALL-E")

    client = OpenAI(api_key=settings.OPEN_API_KEY)

    response = client.images.generate(
      model="dall-e-3",
      prompt= format_dalle_prompt(title = title, image_description = prompt),
      size="1792x1024",
      quality="standard",
      n=1,
      style = style
    )

    image_url = response.data[0].url
    response = requests.get(image_url)
    x = str(uuid.uuid4())
    open(rf"{dir_name}{x}.png", "wb").write(response.content)

    return rf"{dir_name}{x}.png"


def generate_from_diffusion(prompt: str, dir_name: str, title: str = "", *args, **kwargs):

    url = "https://stablediffusionapi.com/api/v3/text2img"

    if not settings.DIFFUSION_KEY:
        logger.error("Tried to call diffusion but no api key")
        return

    logger.warning("Api call in diffusion")
    payload = json.dumps({
                    "key": settings.DIFFUSION_KEY,
                    "prompt": format_dalle_prompt(title = title, image_description = prompt),
                    "negative_prompt": None,
                    "width": "1024",
                    "height": "1024",
                    "samples": "1",
                    "num_inference_steps": "20",
                    "guidance_scale": 7.5,
                    })

    headers = {'Content-Type': 'application/json'}

    response = requests.post(url, headers = headers, data = payload)
    image = response.json()['output'][0]
    filename = str(uuid.uuid4())
    urllib.request.urlretrieve(image, f"{dir_name}\\{filename}.png")
    return f"{dir_name}\\{filename}.png"


def generate_from_midjourney(prompt: str, dir_name: str, title: str = "", *args, **kwargs):
    if not settings.MIDJOURNEY_KEY:
        logger.error("Tried to call MIDJOURNEY but no api key")
        return

    logger.warning("Api call in midjourney")
    payload = {"prompt": format_dalle_prompt(title, prompt)}
    headers = {"Authorization": f"Bearer {settings.MIDJOURNEY_KEY}"}
    response = requests.post("https://api.mymidjourney.ai/api/v1/midjourney/imagine",
                             headers = headers,
                             data = payload).json()

    if not response["success"]:
        logger.error("Failed to generate image with midjourney")
        return

    image = requests.get(f"https://api.mymidjourney.ai/api/v1/midjourney/message/{response['messageId']}",
                         headers).json()['uri']

    filename = str(uuid.uuid4())
    urllib.request.urlretrieve(image, f"{dir_name}\\{filename}.png")
    return f"{dir_name}\\{filename}.png"


def create_image_scene(prompt: str, image: str, text: str, dir_name: str, mode: str = "WEB", provider: str = None,
                       style: str = "", title: str = "") -> None:

    provider = default_providers.get(mode) if provider is None else provider
    scene = Scene.objects.get(prompt = prompt, text = text.strip())
    try:
        downloaded_image = getattr(thismodule, modes.get(mode, "WEB").get(provider))(image,
                                                                                     f'{dir_name}/images/',
                                                                                     style = style,
                                                                                     title = title)
    except Exception as ex:
        logger.error(ex)
        downloaded_image = None

    SceneImage.objects.create(scene = scene, file = downloaded_image, prompt = image)


def create_image_scenes(video: Videos, mode: str = "WEB", style: str = "natural") -> None:
    is_sentenced = True if video.prompt.template is None else video.prompt.template.is_sentenced
    dir_name = video.dir_name
    search_field = "scene" if "scene" in video.gpt_answer["scenes"][0] and \
                              isinstance(video.gpt_answer["scenes"][0]["scene"],list) \
                              else "section" if "section" in video.gpt_answer["scenes"][0] else "sentences"

    narration_field = "sentence" if "sentence" in video.gpt_answer["scenes"][0][search_field][0] else "narration"

    for j in video.gpt_answer['scenes']:
        if is_sentenced:
            for x in j[search_field]:
                create_image_scene(video.prompt,
                                   x['image_description'],
                                   x[narration_field],
                                   dir_name,
                                   mode=mode,
                                   style=style,
                                   title = video.title)

        else:
            create_image_scene(video.prompt,
                               j['image'],
                               j['dialogue'],
                               dir_name,
                               mode=mode,
                               style=style,
                               title = video.title)


def generate_new_image(scene_image: SceneImage, video: Videos, style: str = "vivid") -> SceneImage:
    provider = default_providers.get(video.mode)
    try:
        img = modes.get(video.mode).get(provider)(scene_image.prompt, f'{video.dir_name}/images/', style = style,
                                                  title = video.title)
    except Exception as ex:
        logger.error(ex)
        img = None
        pass

    if img:
        scene_image.file = img
        scene_image.save()

    return scene_image


def create_twitch_clip_scene(clip: str, title: str, prompt: str) -> None:
    splited_clip = split_video_and_mp3(clip)
    edited_video = add_text_to_video(splited_clip[1], title, x = 80, y = 900)

    curr_scene = Scene.objects.create(file = splited_clip[0], prompt = prompt, text = title,
                                      is_last = True)

    SceneImage.objects.create(scene = curr_scene, file = edited_video, prompt = "twitch video")
