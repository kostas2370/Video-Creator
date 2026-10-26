import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from django.db import close_old_connections

from apps.apikeysmanagement.models import Provider
from apps.videomanagement.integrations.visuals import ImageProviderRegistry
from apps.videomanagement.models import ImageMode, Scene, SceneImage, Video, VideoType
from apps.videomanagement.utils.audio_editing import duration_override
from apps.videomanagement.utils.file_utils import check_if_video, stored_file_exists
from apps.videomanagement.utils.frames import still_from_video
from apps.videomanagement.utils.prompt_utils import (
    script_lines, with_shot_plan, with_visual_continuity,
)
from apps.videomanagement.utils.timing import file_timing

logger = logging.getLogger(__name__)
MAX_PARALLEL_STILL_IMAGES = 3


def scene_narration_duration(scene: Scene) -> float:
    return file_timing(scene.file).get("audio_duration") or 0


def visual_generation_duration(scene):
    if (scene.video.settings or {}).get("narration", True):
        return scene_narration_duration(scene)
    return (
        duration_override(scene)
        or (scene.shot_plan or {}).get("target_duration")
        or scene_narration_duration(scene)
    )


def planned_visual_prompt(scene, prompt, mode, provider):
    if mode != ImageMode.AI:
        return prompt
    return with_visual_continuity(
        with_shot_plan(
            prompt, scene.shot_plan or {},
            video=ImageProviderRegistry.is_video(provider, user=scene.video.created_by, mode=mode),
        ),
        (scene.video.settings or {}).get("visual_continuity", ""),
    )


def continuation_frame(video: Video, text: str, path: str):
    """Use the last visible frame when narration trims the generated clip."""
    if not path:
        return None
    previous = Scene.objects.filter(video=video, text=text.strip()).first()
    duration = (
        scene_narration_duration(previous)
        if previous and (video.settings or {}).get("narration", True)
        else duration_override(previous) if previous else 0
    )
    options = {"end_time": duration} if duration else {}
    return still_from_video(path, f"{video.dir_name}/images/", **options)


def uploaded_reference(video, provider):
    """Style-only video references guide text without imposing a source first frame."""
    if not video.reference_image or not stored_file_exists(video.reference_image):
        return None
    if (video.settings or {}).get("reference_role") == "style" and ImageProviderRegistry.is_video(
        provider, user=video.created_by,
    ):
        return None
    return video.reference_image.path


def reference_role_for(video, reference):
    if reference and video.reference_image and reference == video.reference_image.path:
        return (video.settings or {}).get("reference_role", "both")
    # Generated identity anchors and preceding clip frames keep their whole look.
    return "both"


def create_image_scene(
    video: Video,
    image: str,
    text: str,
    dir_name: str,
    mode: str = ImageMode.WEB,
    provider: str = None,
    style: str = "vivid",
    title: str = "",
    reference: str = None,
    with_audio: bool = False,
    user=None,
    *args,
    **kwargs,
) -> str:
    """
    Create a scene with an image and text.

    Parameters:
    -----------
    video : Video
        The video the scene belongs to.
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
    with_audio : bool, optional
        Whether the scene should play the visual's own sound. Only ever true for a
        generated video clip — a still has nothing to play.

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
    scene = Scene.objects.filter(video=video, text=text.strip()).first()
    if scene is None:
        logger.error("No scene for %r; skipping its visual", text[:60])
        return None

    try:
        generate = ImageProviderRegistry.resolve(mode, provider)
        downloaded_image = generate(
            planned_visual_prompt(scene, image, mode, provider),
            f"{dir_name}/images/",
            style=style,
            title=title,
            duration=visual_generation_duration(scene),
            video_format=(video.settings or {}).get("video_format", "LANDSCAPE"),
            reference=reference,
            reference_role=reference_role_for(video, reference),
            user=user,
        )
    except Exception as ex:
        logger.error(ex)
        downloaded_image = None

    SceneImage.objects.create(
        scene=scene,
        file=downloaded_image,
        prompt=image,
        with_audio=bool(
            with_audio and downloaded_image and check_if_video(downloaded_image)
        ),
    )
    return downloaded_image


def existing_visual(video: Video, text: str):
    """Find a usable visual, including after a failed attempt left an empty row."""
    images = SceneImage.objects.filter(
        scene__video=video, scene__archived_at__isnull=True, scene__text=text.strip()
    ).order_by("created_at")
    return next(
        (image.file.path for image in images if stored_file_exists(image.file)), None
    )


def create_image_scenes(
    video: Video,
    mode: str = ImageMode.WEB,
    style: str = "natural",
    provider=None,
    *args,
    **kwargs,
) -> None:
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

    dir_name = video.dir_name
    with_audio = not (video.settings or {}).get("narration", True)
    lines = list(script_lines(video.gpt_answer))
    pending = [line for line in lines if existing_visual(video, line.text) is None]

    if not pending:
        return

    is_video = ImageProviderRegistry.is_video(provider, user=video.created_by, mode=mode)
    shared_image_reference = mode == ImageMode.AI and provider in (
        None,
        "",
        Provider.OPENAI,
    )
    if not is_video and not shared_image_reference:
        with ThreadPoolExecutor(
            max_workers=min(MAX_PARALLEL_STILL_IMAGES, len(pending)),
            thread_name_prefix="scene-image",
        ) as pool:
            futures = [
                pool.submit(
                    _create_image_scene_in_thread,
                    video=video,
                    image=line.image_description,
                    text=line.text,
                    dir_name=dir_name,
                    mode=mode,
                    style=style,
                    title=video.title,
                    provider=provider,
                    with_audio=with_audio,
                    user=video.created_by,
                )
                for line in pending
            ]
            for future in futures:
                future.result()
        return

    reference = uploaded_reference(video, provider)
    for line in lines:
        # Walk completed scenes too, so carry-on recovers the correct reference.
        produced = existing_visual(video, line.text)
        if produced is None:
            produced = create_image_scene(
                video=video,
                image=line.image_description,
                text=line.text,
                dir_name=dir_name,
                mode=mode,
                style=style,
                title=video.title,
                provider=provider,
                reference=reference,
                with_audio=with_audio,
                user=video.created_by,
            )
        if is_video:
            # A failed shot breaks the chain; never continue from a stale frame.
            reference = continuation_frame(video, line.text, produced)
        elif reference is None and produced:
            # Keep the original identity anchor instead of accumulating image drift.
            reference = produced


def _create_image_scene_in_thread(**kwargs):
    close_old_connections()
    try:
        return create_image_scene(**kwargs)
    finally:
        close_old_connections()


def scene_reference(scene: Scene, video: Video, provider):
    """Select an identity anchor or the preceding scene's final frame."""
    if video.mode != ImageMode.AI:
        return None
    uploaded = uploaded_reference(video, provider)
    if provider in (None, "", Provider.OPENAI) and uploaded:
        return uploaded
    if provider in (None, "", Provider.OPENAI):
        for image in SceneImage.objects.filter(scene__video=video, scene__archived_at__isnull=True).order_by(
            "scene__position", "created_at"
        ):
            if stored_file_exists(image.file) and not check_if_video(image.file.path):
                return image.file.path
    elif ImageProviderRegistry.is_video(provider, user=video.created_by):
        previous = (
            video.scenes.filter(position__lt=scene.position)
            .order_by("-position")
            .first()
        )
        if previous is None:
            return uploaded
        return continuation_frame(
            video, previous.text, existing_visual(video, previous.text)
        )
    return None


def generate_new_image(
    scene_image: SceneImage, video: Video, style: str = "vivid", *args, **kwargs
) -> SceneImage:
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
    provider = (video.settings or {}).get("provider")
    mode = video.mode
    if video.video_type == VideoType.MANUAL:
        mode, provider = ImageMode.AI, Provider.OPENAI
        Path(video.dir_name, "images").mkdir(parents=True, exist_ok=True)
    generate = ImageProviderRegistry.resolve(mode, provider)
    if "reference" not in kwargs:
        kwargs["reference"] = scene_reference(scene_image.scene, video, provider)
    kwargs.setdefault("reference_role", reference_role_for(video, kwargs["reference"]))
    kwargs.setdefault("duration", visual_generation_duration(scene_image.scene))
    kwargs.setdefault("video_format", (video.settings or {}).get("video_format", "LANDSCAPE"))
    img = generate(
        planned_visual_prompt(scene_image.scene, scene_image.prompt or "", mode, provider),
        f"{video.dir_name}/images/",
        *args,
        style=style,
        title=video.title,
        user=video.created_by,
        **kwargs,
    )

    if not img:
        raise RuntimeError("The visual provider returned no image")
    scene_image.file = img
    scene_image.save()

    return scene_image
