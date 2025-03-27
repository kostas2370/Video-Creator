import json
import logging
import os
import sys
import urllib.request
import uuid

import requests
from django.conf import settings
from openai import OpenAI
from pytubefix import YouTube, Playlist

from .bing_image_downloader import downloader
from .exceptions import FileNotDownloadedException
from .google_image_downloader import downloader as google_downloader
from .mapper import modes, default_providers
from .prompt_utils import format_dalle_prompt, determine_fields
from .video_utils import add_text_to_video
from ..models import Music, Scene, SceneImage, Video

logger = logging.getLogger(__name__)

thismodule = sys.modules[__name__]


def download_playlist(url: str, category: str) -> None:
    """
    Download a playlist of videos as audio files and save them as MP3 files.

    Parameters:
    -----------
    url : str
        The URL of the playlist.
    category : str
        The category of the playlist.

    Returns:
    --------
    None

    Notes:
    ------
    - This function uses pytube library to download each video in the playlist as an audio file (MP3).
    - The downloaded audio files are saved in the 'media/music' directory.
    - Each downloaded audio file is renamed with a unique filename generated using uuid.
    - Information about each downloaded music file is stored in the Music model.
    """

    playlist = Playlist(url)
    for music in playlist.videos:
        stream = music.streams.filter(only_audio = True).first()
        try:

            filename = str(uuid.uuid4())
            song = stream.download('media/music')
            new_file = f'media/music/{filename}.mp3'
            if not os.path.isfile(song):
                raise FileNotDownloadedException()

            os.rename(song, new_file)

            Music.objects.create(name = stream.title, file = new_file, category = category)

        except FileNotDownloadedException:
            logger.error("Error downloading song")


def download_image(query: str, path: str, amount: int = 1, *args, **kwargs) -> list[str]:
    """
    Download images from Bing using a downloader.

    Parameters:
    -----------
    query : str
        The search query for images.
    path : str
        The directory path where the downloaded images will be saved.
    amount : int, optional
        The number of images to download. Default is 1.
    *args, **kwargs : additional arguments and keyword arguments
        Additional arguments and keyword arguments to pass to the downloader.

    Returns:
    --------
    list of str
        The list of paths to the downloaded images.

    Notes:
    ------
    - This function uses a downloader to download images from Bing based on the provided search query.
    - The downloaded images are saved in the specified directory path.
    - The number of images to download can be specified using the 'amount' parameter.
    - Additional arguments and keyword arguments can be passed to the downloader.
    """
    try:
        logger.info("Downloading image from bing")
        return downloader.download(query = f'{query}', limit = amount, output_dir = path,
                                   adult_filter_off = True,
                                   force_replace = False, timeout = 60, filter = 'photo')[0]

    except Exception as exc:
        logger.error(f"Error downloading image with query {query} Error {exc}")


def download_image_from_google(q: str, path: str, amt: int = 1, *args, **kwargs) -> str:
    """
    Download images from Google using a downloader.

    Parameters:
    -----------
    q : str
        The search query for images.
    path : str
        The directory path where the downloaded images will be saved.
    amt : int, optional
        The number of images to download. Default is 1.
    *args, **kwargs : additional arguments and keyword arguments
        Additional arguments and keyword arguments to pass to the downloader.

    Returns:
    --------
    str
        The path to the downloaded image.

    Notes:
    ------
    - This function uses a downloader to download images from Google based on the provided search query.
    - The downloaded image is saved in the specified directory path.
    - The number of images to download can be specified using the 'amt' parameter.
    - Additional arguments and keyword arguments can be passed to the downloader.
    """
    try:
        logger.info("Downloading image from google")
        return google_downloader.download(q = q, path = path, amt = amt)

    except Exception as exc:
        logger.error(f"Error downloading image with query {q} Error {exc}")


def download_video(url: str, dir_name: str, *args, **kwargs) -> str:
    """
    Download a video from YouTube.

    Parameters:
    -----------
    url : str
        The URL of the video.
    dir_name : str
        The directory path where the downloaded video will be saved.

    Returns:
    --------
    str
        The path to the downloaded video file.

    Notes:
    ------
    - This function uses the pytube library to download the video from the provided YouTube URL.
    - The downloaded video is saved in the specified directory path.
    - The file name of the downloaded video is based on the video's title.
    """

    yt = YouTube(url)
    video = yt.streams.get_highest_resolution()
    video.download(dir_name)
    return f'{dir_name}{yt.title}.mp4'


def download_music(url: str) -> str:
    """
    Download music from YouTube and save it as an MP3 file.

    Parameters:
    -----------
    url : str
        The URL of the YouTube video containing the music.

    Returns:
    --------
    str
        The path to the downloaded MP3 file, or None if the URL is invalid.

    Notes:
    ------
    - This function downloads the audio from the provided YouTube video URL.
    - The downloaded audio is saved as an MP3 file in the 'media/music' directory.
    - If the same music is already downloaded, it returns the existing Music object without downloading again.
    """

    if url is None or url == "None" or url == "":
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
    """
    Generate an image using the DALL-E model.

    Parameters:
    -----------
    prompt : str
        The prompt for generating the image.
    dir_name : str
        The directory path where the generated image will be saved.
    style : str
        The style for generating the image.
    title : str, optional
        The title for the image. Default is an empty string.

    Returns:
    --------
    str
        The path to the generated image file.

    Notes:
    ------
    - This function uses the OpenAI API to generate an image using the DALL-E model.
    - The generated image is saved in the specified directory path.
    - The filename of the generated image is a UUID followed by '.png'.
    """
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
    """
    Generate an image using the Diffusion model.

    Parameters:
    -----------
    prompt : str
        The prompt for generating the image.
    dir_name : str
        The directory path where the generated image will be saved.
    title : str, optional
        The title for the image. Default is an empty string.
    *args, **kwargs : additional arguments and keyword arguments
        Additional arguments and keyword arguments to pass to the diffusion model API.

    Returns:
    --------
    str
        The path to the generated image file.

    Notes:
    ------
    - This function uses the Diffusion model API to generate an image based on the provided prompt.
    - The generated image is saved in the specified directory path.
    - The filename of the generated image is a UUID followed by '.png'.
    """

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
    """
    Generate an image using the Midjourney API.

    Parameters:
    -----------
    prompt : str
        The prompt for generating the image.
    dir_name : str
        The directory path where the generated image will be saved.
    title : str, optional
        The title for the image. Default is an empty string.


    Returns:
    --------
    str
        The path to the generated image file.

    Notes:
    ------
    - This function uses the Midjourney API to generate an image based on the provided prompt.
    - The generated image is saved in the specified directory path.
    - The filename of the generated image is a UUID followed by '.png'.
    """
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
                       style: str = "vivid", title: str = "", *args, **kwargs) -> None:
    """
    Create a scene with an image and text.

    Parameters:
    -----------
    prompt : str
        The prompt associated with the scene.
    image : str
        The image URL or path.
    text : str
        The text content for the scene.
    dir_name : str
        The directory path where the image will be saved.
    mode : str, optional
        The mode for image downloading. Default is "WEB".
    provider : str, optional
        The provider for image downloading. Default is None.
    style : str, optional
        The style for image generation (applicable if mode is not "WEB"). Default is an empty string.
    title : str, optional
        The title for the image (applicable if mode is not "WEB"). Default is an empty string.

    Returns:
    --------
    None

    Notes:
    ------
    - This function creates a scene with an image.
    - The image is downloaded or generated based on the mode and provider specified.
    - The downloaded image is saved in the specified directory path.
    - If an exception occurs during image downloading or creation, it is logged,
      and the scene is created with a None image.
    """
    provider = default_providers.get(mode) if not provider else provider
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


def create_image_scenes(video: Video, mode: str = "WEB", style: str = "natural", provider=None, *args, **kwargs) -> None:
    """
    Create image scenes for a video.

    Parameters:
    -----------
    video : Videos
        The video object for which image scenes are created.
    mode : str, optional
        The mode for image downloading. Default is "WEB".
    style : str, optional
        The style for image generation. Default is "natural".

    Returns:
    --------
    None

    Notes:
    ------
    - This function iterates over scenes in a video's GPT answer and creates image
      scenes based on the scene descriptions.
    - The mode and style parameters determine the method and style of image creation.
    """

    is_sentenced = True if video.prompt.template is None else video.prompt.template.is_sentenced
    dir_name = video.dir_name
    first_scene = video.gpt_answer["scenes"][0]
    search_field, narration_field = determine_fields(first_scene)
    for j in video.gpt_answer['scenes']:
        if is_sentenced:
            for x in j[search_field]:
                create_image_scene(
                    prompt = video.prompt,
                    image = x['image_description'],
                    text = x[narration_field],
                    dir_name = dir_name,
                    mode = mode,
                    style = style,
                    title = video.title,
                    provider = provider
                )

        else:
            create_image_scene(
                prompt = video.prompt,
                image = j['image'],
                text = j['dialogue'],
                dir_name = dir_name,
                mode=mode,
                style=style,
                title = video.title
            )


def generate_new_image(scene_image: SceneImage, video: Video, style: str = "vivid", *args, **kwargs) -> SceneImage:
    """
    Generate a new image for a scene image associated with a video.

    Parameters:
    -----------
    scene_image : SceneImage
        The scene image object for which a new image is generated.
    video : Videos
        The video object associated with the scene image.
    style : str, optional
        The style for image generation. Default is "vivid".

    Returns:
    --------
    SceneImage
        The updated scene image object with the new image.

    """
    provider = default_providers.get(video.mode)

    if not provider or not modes.get(video.mode):
        logger.error(f"Invalid video mode or provider not found for video {video.id}.")
        return scene_image

    try:
        img_gen_method = getattr(thismodule, modes.get(video.mode).get(provider))

        img = img_gen_method(scene_image.prompt, f'{video.dir_name}/images/', style = style, title = video.title, *args,
                             **kwargs)

    except AttributeError as attr_err:
        logger.error(f"Method not found for provider {provider} in mode {video.mode}: {attr_err}")
        img = None
    except Exception as ex:
        logger.error(f"Error generating image for video {video.id}: {ex}")
        img = None

    if img:
        scene_image.file = img
        scene_image.save()

    return scene_image


def create_twitch_clip_scene(clip: str, title: str, prompt: str) -> None:
    """
    Create a scene for a Twitch clip.

    Parameters:
    -----------
    clip : str
        The path to the Twitch clip.
    title : str
        The title of the Twitch clip.
    prompt : str
        The prompt associated with the Twitch clip.

    Returns:
    --------
    None

    Notes:
    ------
    - This function splits the Twitch clip into video and audio components, adds text to the video,
      and creates the scene and associated scene image objects.
    """

    edited_video = add_text_to_video(clip, title)

    curr_scene = Scene.objects.create(prompt = prompt, text = title,
                                      is_last = True)

    SceneImage.objects.create(scene = curr_scene, file = edited_video, prompt = "twitch video", with_audio = True)
