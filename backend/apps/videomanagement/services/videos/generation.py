import logging
import tempfile
from concurrent.futures import ThreadPoolExecutor
from typing import Literal, Union
from uuid import uuid4

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import close_old_connections
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from slugify import slugify

from apps.usage.models import GenerationEstimate
from apps.usage.scenarios import project_estimate
from apps.usage.services import video_usage
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
from apps.videomanagement.prompts.storyboard import (
    build_script_prompt,
    build_text_storyboard_prompt,
)
from apps.videomanagement.services.captions.transcription import transcribe_audio
from apps.videomanagement.services.media.catalog import (
    create_catalog_music,
    select_music_track,
)
from apps.videomanagement.services.media.downloads import download_music
from apps.videomanagement.services.media.icons import icon_candidates
from apps.videomanagement.services.media.music_search import import_search_music
from apps.videomanagement.services.media.selection import available_voice, owned_asset
from apps.videomanagement.services.scenes.narration import (
    ensure_scene_rows,
    make_scenes_speech,
)
from apps.videomanagement.services.scenes.visual_planning import apply_visual_plans
from apps.videomanagement.services.scenes.visuals import create_image_scenes
from apps.videomanagement.utils.file_utils import generate_directory

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
    GenerationEstimate.objects.get_or_create(
        video=video, defaults={"estimate": project_estimate(video)}
    )
    if video.source_audio:
        from apps.videomanagement.services.videos.audio import prepare_audio_scenes

        prepare_audio_scenes(video)
        if image_mode:
            create_image_scenes(video, mode=image_mode, style=style, provider=provider)
    elif not image_mode or ImageProviderRegistry.is_video(
        provider, user=video.created_by, mode=image_mode
    ):
        make_scenes_speech(video)
        if image_mode:
            create_image_scenes(video, mode=image_mode, style=style, provider=provider)
    else:
        # Images look up their Scene rows, so finish creating the full script before either
        # worker starts. Two workers overlap the independent provider requests without
        # adding unbounded load to TTS, image providers, or the database.
        ensure_scene_rows(video)
        with ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="video-assets"
        ) as pool:
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
    apply_visual_plans(video)


def create_pending_video(
    message: str,
    created_by: get_user_model(),
    video_type: Literal["AI"] = "AI",
    title: str = None,
    genre: str = "",
) -> Video:
    """
    Create the pending Video row for its selected generation flow.

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
        operation_id=uuid4(),
        video_type=video_type,
        created_by=created_by,
        genre=genre,
    )


def generate_video(video: Video, **params) -> Video:
    """Route existing queued jobs to the appropriate input flow."""
    if video.source_audio:
        return generate_audio_video(video, **params)
    if "source_text" in params:
        return generate_text_video(video, **params)
    return generate_idea_video(video, **params)


def _generation_assets(video, choices):
    """Resolve owned assets before any paid storyboard or transcription request."""
    avatar = owned_asset(Avatar, choices.get("avatar_selection"), video.created_by)
    intro = owned_asset(Intro, choices.get("intro"), video.created_by)
    outro = owned_asset(Outro, choices.get("outro"), video.created_by)
    voice = (
        None
        if video.source_audio
        else (
            avatar.voice
            if avatar
            else available_voice(choices["voice_id"], video.created_by)
            if choices.get("voice_id")
            else VoiceModel.select_voice(video.created_by)
        )
    )
    return avatar, intro, outro, voice


def _planning_options(video, choices):
    image_mode = choices.get("image_mode")
    has_reference = bool(image_mode == "AI" and video.reference_image)
    return dict(
        scene_count=choices.get("scene_count"),
        image_mode=image_mode,
        video=ImageProviderRegistry.is_video(
            choices.get("provider"), user=video.created_by, mode=image_mode
        ),
        style=choices.get("style", "natural"),
        video_audio_mode=(video.settings or {}).get("video_audio_mode", "AUTO"),
        ai_scene_editing=choices.get("ai_scene_editing", False),
        diagram_icons=icon_candidates(choices["message"], user=video.created_by_id)
        if choices.get("ai_scene_editing")
        else (),
        visual_continuity=choices.get("visual_continuity", ""),
        reference_role=choices.get("reference_role", "both") if has_reference else None,
    )


def _request_storyboard(video, prompt, choices, planning):
    with video_usage(video):
        return get_reply(
            prompt,
            gpt_model=choices.get("gpt_model"),
            user=video.created_by,
            narration=choices.get("narration", True),
            scene_count=choices.get("scene_count"),
            ai_scene_editing=choices.get("ai_scene_editing", False),
            video_provider=planning["video"],
            require_visual_continuity=choices.get("image_mode") == "AI",
            **(
                {"require_episode_summary": True}
                if choices.get("series_context")
                else {}
            ),
            **(
                {"reference_image": video.reference_image.path}
                if planning["reference_role"]
                else {}
            ),
        )


def _narration_storyboard(video, source_text, choices):
    """Text and recorded narration share exact-word visual planning."""
    planning = _planning_options(video, choices)
    prompt = build_text_storyboard_prompt(source_text, **planning)
    storyboard = _request_storyboard(video, prompt, choices, planning)
    imported = " ".join(
        shot.get("sentence", "")
        for scene in storyboard["scenes"]
        for shot in scene["sentences"]
    )
    if imported.split() != source_text.split():
        raise APIException(
            "The storyboard changed your script. Please try again; no media was generated."
        )
    return storyboard


def generate_idea_video(video: Video, **choices) -> Video:
    """Write a storyboard from an idea, then use the shared production pipeline."""
    assets = _generation_assets(video, choices)
    storyboard = None
    if not (video.gpt_answer and video.dir_name):
        planning = _planning_options(video, choices)
        prompt = build_script_prompt(
            genre=choices.get("genre", ""),
            userprompt=choices["message"],
            target_audience=choices.get("target_audience", ""),
            narration_language=choices.get("narration_language", ""),
            platform=choices.get("platform", "GENERAL"),
            narration=choices.get("narration", True),
            **planning,
        )
        prompt += choices.get("series_context", "")
        storyboard = _request_storyboard(video, prompt, choices, planning)
    return _complete_video_generation(
        video, storyboard=storyboard, assets=assets, **choices
    )


def generate_text_video(video: Video, *, source_text: str, **choices) -> Video:
    """Plan visuals around supplied text and preserve intentional review edits."""
    if not source_text.strip():
        raise ValidationError("Add your script to continue.")
    assets = _generation_assets(video, choices)
    storyboard = None
    if not (video.gpt_answer and video.dir_name):
        storyboard = _narration_storyboard(video, source_text, choices)
    return _complete_video_generation(
        video, storyboard=storyboard, assets=assets, **choices
    )


def generate_audio_video(video: Video, **choices) -> Video:
    """Transcribe a recording directly, plan its visuals, and keep its original voice."""
    if not video.source_audio:
        raise ValidationError("Upload an MP3 or WAV recording to continue.")
    choices.pop("source_text", None)
    choices.update(
        avatar_selection="", voice_id=None, narration=True, narration_language=""
    )
    assets = _generation_assets(video, choices)
    if not video.source_audio_words:
        with (
            tempfile.TemporaryDirectory(prefix="audio-storyboard-") as directory,
            video_usage(video),
        ):
            words = transcribe_audio(
                video.source_audio.path,
                video.created_by,
                video.source_audio_duration,
                directory,
            )
        if not words:
            raise ValidationError(
                "No speech was detected in this recording. Choose a recording with clear spoken narration."
            )
        video.source_audio_words = words
        video.save(update_fields=["source_audio_words"])
    source_text = " ".join(word["text"] for word in video.source_audio_words)
    if len(source_text) > 20000:
        raise ValidationError(
            "This recording has too much speech. Choose a shorter recording (up to 20,000 transcript characters)."
        )
    storyboard = None
    if not (video.gpt_answer and video.dir_name):
        storyboard = _narration_storyboard(video, source_text, choices)
    return _complete_video_generation(
        video, storyboard=storyboard, assets=assets, **choices
    )


def _complete_video_generation(
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
    review_starting_frames: bool = False,
    ai_scene_editing: bool = False,
    visual_continuity: str = "",
    reference_role: str = "both",
    series_context: str = "",
    generation_mode: str = "STANDARD",
    narration_language: str = "",
    storyboard: dict = None,
    assets: tuple = (),
) -> Video:
    """Persist a prepared storyboard, stop for review, or generate its media."""
    selected_avatar, intro, outro, voice_model = assets

    logger.info("Retrieved template")
    video_provider = ImageProviderRegistry.is_video(
        provider, user=video.created_by, mode=image_mode
    )
    has_reference = bool(image_mode == "AI" and video.reference_image)
    new_script = not (video.gpt_answer and video.dir_name)
    if not new_script:
        logger.info("Resuming video %s from its saved storyboard", video.id)
        x = video.gpt_answer
        dir_name = video.dir_name
    else:
        if storyboard is None:
            raise APIException("No storyboard was prepared for this video.")
        x = storyboard
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
    audio_settings = {
        key: vid.settings[key]
        for key in ("video_audio_mode", "video_audio_enabled", "music_volume")
        if key in (vid.settings or {})
    }
    vid.settings = dict(
        subtitles=subtitles,
        narration=narration,
        narration_language=narration_language,
        avatar_position=avatar_position,
        video_format=video_format,
        platform=platform,
        style=style,
        provider=provider,
        generation_mode=generation_mode,
        gpt_model=gpt_model or settings.DEFAULT_GPT_MODEL,
    )
    vid.settings.update(audio_settings)
    if vid.source_audio:
        vid.settings["creation_mode"] = "AUDIO"
    if music == "auto":
        vid.settings["auto_music"] = True
    elif music and music.startswith(("ai:", "catalog:")):
        vid.settings["music_selection"] = music
    if review_starting_frames:
        vid.settings["review_starting_frames"] = True
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
        vid.settings["visual_type"] = "VIDEO" if video_provider else "IMAGE"
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
        if music == "auto":
            if not vid.music_id:
                vid.music = create_catalog_music(
                    select_music_track(vid), user=vid.created_by
                )
        elif music and music.startswith(("ai:", "catalog:")):
            vid.music = import_search_music(vid, music, editing=False)
        else:
            vid.music = download_music(music, user=vid.created_by)
    except Exception as exc:
        if music and music.startswith(("ai:", "catalog:")):
            raise
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

    if choices.get("auto_music") and not video.music_id:
        try:
            video.music = create_catalog_music(
                select_music_track(video), user=video.created_by
            )
        except Exception as exc:
            logger.error(exc)
    elif choices.get("music_selection") and not video.music_id:
        video.music = import_search_music(
            video, choices["music_selection"], editing=False
        )

    video.status = VideoStatus.READY
    video.save()

    return video
