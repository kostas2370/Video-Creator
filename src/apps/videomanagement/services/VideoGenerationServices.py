import logging
from typing import Union, Literal

from slugify import slugify

from ..defaults import default_format
from ..models import TemplatePrompt, Video, VoiceModel, UserPrompt, Avatar, Intro, Outro
from ..utils.audio_utils import make_scenes_speech
from ..utils.file_utils import generate_directory
from ..utils.gpt_utils import get_reply
from ..utils.prompt_utils import format_prompt
from ..utils.visual_utils import create_image_scenes, download_music
from ..utils.cost_utils import charge_user
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)


def create_pending_video(
    message: str,
    created_by: get_user_model(),
    video_type: Literal["AI", "TWITCH"] = "AI",
    title: str = None,
) -> Video:
    """
    Create the Video row that `generate_video` will later fill in.

    This is the only part of generation that is cheap enough to run inside a request:
    it gives the caller an id to poll while the real work happens on a worker. The
    video starts in GENERATION with no `gpt_answer`; the title is a placeholder until
    the model returns a real one.
    """
    user_prompt = UserPrompt.objects.create(template=None, prompt=f"{message}")

    return Video.objects.create(
        title=(title or message)[:50],
        prompt=user_prompt,
        dir_name="",
        status="GENERATION",
        video_type=video_type,
        created_by=created_by,
    )


def generate_video(
    video: Video,
    template_id: Union[str, int, None],
    message: str,
    gpt_model: Union[str, None],
    image_mode: Union[str, bool, Literal["WEB", "AI"]],
    avatar_selection: Union[str],
    style: Literal["vivid", "natural"],
    target_audience: str,
    music: Union[str, None] = None,
    background: str = None,
    intro: str = None,
    outro: str = None,
    voice_id: Union[int, None] = None,
    subtitles: bool = False,
    provider: Union[str, None] = None,
    avatar_position: str = "top,right",
) -> Video:
    """
    Generate a video based on the provided parameters.

    Parameters:
    -----------
    video : Video
        The pending video created by `create_pending_video`, filled in here.
    template_id : Union[str, int, None]
        The ID of the template used for the video.
    message : str
        The main message or prompt for the video.
    gpt_model : Union[str, None]
        The GPT model to use for generating text.
    image_mode : Union[str, bool, Literal["WEB", "AI"]]
        The source of images for the video.
    avatar_selection : Union[str]
        The selection of an avatar for the video.
    style : Literal["vivid", "natural"]
        The style of the video.
    target_audience : str
        The target audience for the video.
    music : Union[str, None], optional
        The music to be included in the video.
    background : str, optional
        The background for the video.
    intro : str, optional
        The ID of the intro to be included in the video.
    outro : str, optional
        The ID of the outro to be included in the video.
    voice_id : Union[int, None], optional
        The ID of the voice model to be used.
    subtitles : bool, optional
        Whether to include subtitles in the video.
    provider : Union[str, None], optional
        The provider for generating images.
    avatar_position : str, optional
        The position of the avatar in the video (default is "top,right").

    Returns:
    --------
    Videos
        The generated video object.

    Notes:
    ------
    - This function generates a video based on the provided parameters.
    - It retrieves a template, formats a prompt, and generates video content using various sources for text, images,
      and audio.
    """
    avatar_selection = int(avatar_selection) if avatar_selection.isnumeric() else None

    template = TemplatePrompt.get_template(template_id)
    logger.info("Retrieved template")

    template_format = template.format if template else default_format
    category = (
        template.category
        if template
        else template_id
        if len(template_id) > 0 and not template_id.isnumeric()
        else ""
    )

    prompt = format_prompt(
        template_format=template_format,
        template_category=category,
        userprompt=message,
        target_audience=target_audience,
    )

    x = get_reply(prompt, gpt_model=gpt_model)

    user_prompt = video.prompt
    user_prompt.template = template
    user_prompt.save()
    logger.info(f"Updated the user_prompt instance with id : {user_prompt.id}")

    dir_name = generate_directory(f"media/videos/{slugify(x['title'])}")

    if intro and outro:
        intro = Intro.objects.get(id=int(intro))
        outro = Outro.objects.get(id=int(outro))

    vid = video
    vid.title = x["title"][:50]
    vid.dir_name = dir_name
    vid.gpt_answer = x
    vid.background = background
    vid.intro = intro
    vid.outro = outro
    vid.settings = dict(subtitles=subtitles, avatar_position=avatar_position)
    vid.save()

    logger.info(f"Filled in the video instance with id : {vid.id}")

    if avatar_selection:
        selected_avatar = Avatar.select_avatar(selected=avatar_selection)
        voice_model = selected_avatar.voice
        vid.avatar = selected_avatar

    else:
        voice_model = (
            VoiceModel.objects.get(id=voice_id)
            if voice_id
            else VoiceModel.select_voice()
        )

    vid.voice_model = voice_model
    vid.save()

    make_scenes_speech(vid)

    logger.info(f"Generated the scenes audios for the video with id : {vid.id}")
    try:
        vid.music = download_music(music)
    except Exception as exc:
        logger.error(exc)

    if image_mode:
        vid.mode = image_mode
        create_image_scenes(vid, mode=image_mode, style=style, provider=provider)
        logger.info(f"Generated the images for the video with id : {vid.id}")

    vid.status = "READY"
    vid.save()

    charge_user(vid.created_by, "generation_limit_for_ai", vid)

    return vid
