import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Literal, Union

from django.contrib.auth import get_user_model
from django.db import close_old_connections
from apps.usage.services import video_usage
from rest_framework import status
from rest_framework.exceptions import APIException
from slugify import slugify

from apps.videomanagement.hooks import run_video_hooks
from apps.videomanagement.integrations.llm import get_reply
from apps.videomanagement.integrations.visuals import ImageProviderRegistry
from apps.videomanagement.models import (
    Avatar,
    Intro,
    Outro,
    UserPrompt,
    Video,
    VideoStatus,
    VoiceModel,
)
from apps.videomanagement.services.media.downloads import download_music
from apps.videomanagement.services.media.selection import available_voice, owned_asset
from apps.videomanagement.services.scenes.narration import (
    ensure_scene_rows,
    make_scenes_speech,
)
from apps.videomanagement.services.scenes.visuals import create_image_scenes
from apps.videomanagement.utils.file_utils import generate_directory
from apps.videomanagement.utils.prompt_utils import build_script_prompt

logger = logging.getLogger(__name__)


def _run_with_thread_db_cleanup(function):
    """Give each generation worker a clean, short-lived Django DB connection."""
    close_old_connections()
    try:
        return function()
    finally:
        close_old_connections()


def generate_scene_assets(video, image_mode=None, style="natural", provider=None):
    """Generate narration and still visuals together when neither depends on the other.

    Video providers stay sequential: they can use narration duration and a previous
    clip's final frame as an input to the next scene.
    """
    from apps.usage.scenarios import project_estimate
    from apps.usage.models import GenerationEstimate

    GenerationEstimate.objects.get_or_create(video=video, defaults={"estimate": project_estimate(video)})
    if not image_mode or ImageProviderRegistry.is_video(
        provider, user=video.created_by, mode=image_mode
    ):
        make_scenes_speech(video)
        if image_mode:
            create_image_scenes(video, mode=image_mode, style=style, provider=provider)
        return

    # Images look up their Scene rows, so finish creating the full script before either
    # worker starts. Two workers overlap the independent provider requests without
    # adding unbounded load to TTS, image providers, or the database.
    ensure_scene_rows(video)
    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="video-assets") as pool:
        narration = pool.submit(
            _run_with_thread_db_cleanup, lambda: make_scenes_speech(video)
        )
        visuals = pool.submit(
            _run_with_thread_db_cleanup,
            lambda: create_image_scenes(
                video, mode=image_mode, style=style, provider=provider
            ),
        )
        narration.result()
        visuals.result()


def create_pending_video(
    message: str,
    created_by: get_user_model(),
    video_type: Literal["AI"] = "AI",
    title: str = None,
    genre: str = "",
) -> Video:
    """
    Create the Video row that `generate_video` will later fill in.

    This is the only part of generation that is cheap enough to run inside a request:
    it gives the caller an id to poll while the real work happens on a worker. The
    video starts in GENERATION with no `gpt_answer`; the title is a placeholder until
    the model returns a real one.
    """
    user_prompt = UserPrompt.objects.create(prompt=f"{message}")

    return Video.objects.create(
        title=(title or message)[:50],
        prompt=user_prompt,
        dir_name="",
        status=VideoStatus.GENERATION,
        video_type=video_type,
        created_by=created_by,
        genre=genre,
    )


def generate_video(
    video: Video,
    message: str,
    gpt_model: Union[str, None],
    image_mode: Union[str, bool, Literal["WEB", "AI"]],
    avatar_selection: Union[str],
    style: Literal["vivid", "natural"],
    target_audience: str,
    music: Union[str, None] = None,
    intro: str = None,
    outro: str = None,
    voice_id: Union[str, None] = None,
    subtitles: bool = False,
    narration: bool = True,
    provider: Union[str, None] = None,
    video_format: str = "LANDSCAPE",
    avatar_position: str = "right,top",
    genre: str = "",
    platform: str = "GENERAL",
    scene_count: int = None,
    review_script: bool = False,
    ai_scene_editing: bool = False,
    visual_continuity: str = "",
    reference_role: str = "both",
    series_context: str = "",
    generation_mode: str = "STANDARD",
) -> Video:
    """
    Generate a video based on the provided parameters.

    Parameters:
    -----------
    video : Video
        The pending video created by `create_pending_video`, filled in here.
    genre :str
        The genre for the video.
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
    intro : str, optional
        The ID of the intro to be included in the video.
    outro : str, optional
        The ID of the outro to be included in the video.
    voice_id : Union[str, None], optional
        The ID of the voice model to be used.
    subtitles : bool, optional
        Whether to include subtitles in the video.
    narration : bool, optional
        Whether to speak the script. With narration off no voice track is produced and
        the scene visuals are concatenated at their own length.
    provider : Union[str, None], optional
        The provider for generating images.
    avatar_position : str, optional
        The position of the avatar in horizontal,vertical order (default is "right,top").

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
    if image_mode == "AI" and provider == "sora":
        raise APIException("Sora is no longer available. Choose another video provider.")
    selected_avatar = owned_asset(Avatar, avatar_selection, video.created_by)
    intro = owned_asset(Intro, intro, video.created_by)
    outro = owned_asset(Outro, outro, video.created_by)
    voice_model = (
        selected_avatar.voice
        if selected_avatar
        else available_voice(voice_id, video.created_by)
        if voice_id
        else VoiceModel.select_voice(video.created_by)
    )

    logger.info("Retrieved template")
    video_provider = ImageProviderRegistry.is_video(
        provider, user=video.created_by, mode=image_mode
    )
    has_reference = bool(image_mode == "AI" and video.reference_image)
    new_script = not (video.gpt_answer and video.dir_name)
    prompt = build_script_prompt(
        genre=genre,
        userprompt=message,
        target_audience=target_audience,
        platform=platform,
        scene_count=scene_count,
        image_mode=image_mode,
        video=video_provider,
        style=style,
        narration=narration,
        ai_scene_editing=ai_scene_editing,
        visual_continuity=visual_continuity,
        reference_role=reference_role if has_reference else None,
    )

    if series_context:
        prompt += series_context

    if video.gpt_answer and video.dir_name:
        logger.info("Resuming video %s from the script it already has", video.id)
        x = video.gpt_answer
        dir_name = video.dir_name
    else:
        with video_usage(video):
            x = get_reply(
                prompt,
                gpt_model=gpt_model,
                user=video.created_by,
                narration=narration,
                scene_count=scene_count,
                ai_scene_editing=ai_scene_editing,
                video_provider=video_provider,
                require_visual_continuity=image_mode == "AI",
                **({"require_episode_summary": True} if series_context else {}),
                **(
                    {"reference_image": video.reference_image.path} if has_reference else {}
                ),
            )
        dir_name = generate_directory(f"media/videos/{slugify(x['title'])}")

    if image_mode == "AI":
        # User preferences win on the initial draft; approval passes the reviewed
        # value (including an explicit blank) back into this same worker.
        if has_reference and new_script:
            # The model merges observed details with explicit user preferences.
            visual_continuity = x.get("visual_continuity") or visual_continuity
        else:
            visual_continuity = visual_continuity or x.get("visual_continuity", "")
        x = {**x, "visual_continuity": visual_continuity}

    user_prompt = video.prompt
    user_prompt.save()
    logger.info(f"Updated the user_prompt instance with id : {user_prompt.id}")

    vid = video
    vid.title = x["title"][:50]
    vid.dir_name = dir_name
    vid.gpt_answer = x
    vid.intro = intro
    vid.outro = outro
    creation_mode = (vid.settings or {}).get("creation_mode")
    character_references = (vid.settings or {}).get("character_references", False)
    generation_params = (vid.settings or {}).get("generation_params")
    vid.settings = dict(
        subtitles=subtitles,
        narration=narration,
        avatar_position=avatar_position,
        video_format=video_format,
        platform=platform,
        style=style,
        provider=provider,
        generation_mode=generation_mode,
    )
    if creation_mode:
        vid.settings["creation_mode"] = creation_mode
    if character_references:
        vid.settings["character_references"] = True
    run_video_hooks(
        "storyboard_generated", video=vid, storyboard=x, new_script=new_script
    )
    if has_reference:
        vid.settings["reference_role"] = reference_role
    if visual_continuity:
        vid.settings["visual_continuity"] = visual_continuity
    if ai_scene_editing:
        vid.settings["ai_scene_editing"] = True
    if scene_count is not None:
        vid.settings["scene_count"] = scene_count
    if review_script:
        if generation_params is not None and image_mode == "AI":
            generation_params = {
                **generation_params,
                "visual_continuity": visual_continuity,
            }
        vid.settings["generation_params"] = generation_params
    vid.save()

    logger.info(f"Filled in the video instance with id : {vid.id}")

    vid.avatar = selected_avatar

    vid.voice_model = voice_model
    vid.save()

    vid.mode = image_mode or None
    vid.save()
    if review_script:
        vid.status = VideoStatus.REVIEW
        vid.save()
        return vid

    generate_scene_assets(vid, image_mode=image_mode, style=style, provider=provider)

    logger.info(f"Generated the scenes audios for the video with id : {vid.id}")
    if image_mode:
        logger.info(f"Generated the images for the video with id : {vid.id}")

    try:
        vid.music = download_music(music, user=vid.created_by)
    except Exception as exc:
        logger.error(exc)

    vid.status = VideoStatus.READY
    vid.save()

    return vid


def resume_video(video: Video) -> Video:
    """Fill in whatever generation did not finish, without paying for it twice.

    Everything a resume needs is on the row already, so it takes no parameters: the
    script, the directory, the voice and the image mode were all settled on the first
    run. Only the scenes with no narration and the sentences with no visual are worked
    on again.
    """
    if not video.gpt_answer or not video.dir_name:
        raise APIException(
            detail="This video never got far enough to resume. Generate it again.",
            code=status.HTTP_409_CONFLICT,
        )

    choices = video.settings or {}
    video.status = VideoStatus.GENERATION
    video.save()

    generate_scene_assets(
        video,
        image_mode=video.mode,
        style=choices.get("style", "natural"),
        provider=choices.get("provider"),
    )
    logger.info("Filled in the missing narration for video %s", video.id)
    if video.mode:
        logger.info("Filled in the missing visuals for video %s", video.id)

    video.status = VideoStatus.READY
    video.save()

    return video
