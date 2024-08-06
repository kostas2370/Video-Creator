from datetime import date
from typing import Literal

from slugify import slugify

from ..models import Videos, UserPrompt
from ..utils.file_utils import generate_directory
from ..utils.twitch import TwitchClient
from ..utils.visual_utils import create_twitch_clip_scene


def generate_twitch_video(
        mode: Literal["game", "streamer"],
        value: str,
        amt: int = 10,
        started_at: str = ""
        ):
    """
    Generate a video based on clips fetched from Twitch.

    Args:
        mode (Literal["game", "streamer"]): The mode of fetching clips, either "game" or "streamer".
        value (str): The value to search for, either the name of a game or a streamer.
        amt (int, optional): The number of clips to fetch. Defaults to 10.
        started_at (str, optional): The starting date/time from which to fetch clips. Defaults to "".

    Returns:
        Videos: The generated video instance.
    """

    message = f"Mode : {mode} Value : {value}"
    title = f"{value} {date.today()}"
    dir_name = generate_directory(f'media/videos/{slugify(title)}')

    user_prompt = UserPrompt.objects.create(template = None, prompt = f'{message}')

    video = Videos.objects.create(prompt = user_prompt,
                                  dir_name = dir_name,
                                  title = title,
                                  status = "GENERATION")

    client = TwitchClient(path = dir_name)
    client.set_headers()

    value = client.get_streamer_id(value) if mode == "streamer" else client.get_game_id(value)
    clips = client.get_clips(value, mode, started_at)

    description = "Source : \n"
    for count, clip in enumerate(clips[:amt]):
        downloaded_clip = client.download_clip(clip)
        if downloaded_clip is None:
            continue

        create_twitch_clip_scene(downloaded_clip, clip.get("title"), video.prompt)
        description += f"{count+1} {clip.get('title')} : {clip.get('url')} \n"

    video.gpt_answer = description
    video.status = "READY"
    video.save()
    return video
