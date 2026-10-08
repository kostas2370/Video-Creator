import logging
import uuid
from concurrent.futures import ThreadPoolExecutor

from django.db import close_old_connections
from moviepy.editor import AudioFileClip, VideoFileClip

from .image_providers import ImageProviderRegistry
from .prompt_utils import script_lines
from .file_utils import check_if_video, stored_file_exists
from ..models import Scene, SceneImage, Video

logger = logging.getLogger(__name__)
MAX_PARALLEL_STILL_IMAGES = 3


def still_from_video(path: str, dir_name: str, end_time: float = None) -> str:
    """Save the last frame of `path` as a png, or return None if it is not a video.

    Used as the opening frame for the next clip in the sequence.
    """
    if not check_if_video(path):
        return None

    frame_path = f"{dir_name}{uuid.uuid4()}.png"
    try:
        with VideoFileClip(path) as clip:
            end = min(clip.duration, end_time) if end_time else clip.duration
            for t in (end - 1 / (clip.fps or 24), end * 0.5, 0):
                try:
                    clip.save_frame(frame_path, t=max(0, t))
                    return frame_path

                except Exception as exc:
                    logger.debug("No frame at %.2fs of %s: %s", t, path, exc)

    except Exception as exc:
        logger.warning("Could not open %s for a style anchor: %s", path, exc)
        return None

    logger.warning("Could not take a style anchor from %s", path)
    return None


def scene_narration_duration(scene: Scene) -> float:
    """Seconds of narration recorded for `scene`, or 0 if it has no audio yet."""
    if not scene.file:
        return 0

    try:
        with AudioFileClip(scene.file.path) as audio:
            return audio.duration

    except Exception as exc:
        logger.warning(
            "Could not read narration length for scene %s: %s", scene.id, exc
        )
        return 0


def continuation_frame(video: Video, text: str, path: str):
    """Use the last visible frame when narration trims the generated clip."""
    if not path:
        return None
    previous = Scene.objects.filter(video=video, text=text.strip()).first()
    duration = (
        scene_narration_duration(previous)
        if previous and (video.settings or {}).get("narration", True)
        else 0
    )
    options = {"end_time": duration} if duration else {}
    return still_from_video(path, f"{video.dir_name}/images/", **options)


def create_image_scene(
    video: Video,
    image: str,
    text: str,
    dir_name: str,
    mode: str = "WEB",
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
            image,
            f"{dir_name}/images/",
            style=style,
            title=title,
            duration=scene_narration_duration(scene),
            reference=reference,
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
        scene__video=video, scene__text=text.strip()
    ).order_by("created_at", "pk")
    return next(
        (image.file.path for image in images if stored_file_exists(image.file)), None
    )


def create_image_scenes(
    video: Video,
    mode: str = "WEB",
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

    is_video = ImageProviderRegistry.is_video(provider, user=video.created_by)
    shared_image_reference = mode == "AI" and provider in (None, "", "OPENAI")
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

    reference = (
        video.reference_image.path
        if video.reference_image and stored_file_exists(video.reference_image)
        else None
    )
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
    if video.mode != "AI":
        return None
    uploaded = (
        video.reference_image.path
        if video.reference_image and stored_file_exists(video.reference_image)
        else None
    )
    if provider in (None, "", "OPENAI") and uploaded:
        return uploaded
    if provider in (None, "", "OPENAI"):
        for image in SceneImage.objects.filter(scene__video=video).order_by("scene__created_at", "scene_id", "created_at", "pk"):
            if stored_file_exists(image.file) and not check_if_video(image.file.path):
                return image.file.path
    elif ImageProviderRegistry.is_video(provider, user=video.created_by):
        previous = video.scenes.filter(created_at__lt=scene.created_at).order_by("-created_at", "-pk").first()
        if previous is None:
            return uploaded
        return continuation_frame(video, previous.text, existing_visual(video, previous.text))
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
    try:
        provider = (video.settings or {}).get("provider")
        generate = ImageProviderRegistry.resolve(video.mode, provider)
        if "reference" not in kwargs:
            kwargs["reference"] = scene_reference(scene_image.scene, video, provider)
        img = generate(
            scene_image.prompt,
            f"{video.dir_name}/images/",
            *args,
            style=style,
            title=video.title,
            user=video.created_by,
            **kwargs,
        )

    except Exception as ex:
        logger.error(f"Error generating image for video {video.id}: {ex}")
        img = None

    if img:
        scene_image.file = img
        scene_image.save()

    return scene_image
