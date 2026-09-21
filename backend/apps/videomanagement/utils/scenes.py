import logging
import uuid

from moviepy.editor import AudioFileClip, VideoFileClip

from .image_providers import resolve
from .prompt_utils import scene_text
from .composer.overlay import add_text_to_video
from .file_utils import check_if_video
from ..models import Scene, SceneImage, Video

logger = logging.getLogger(__name__)


def still_from_video(path: str, dir_name: str) -> str:
    """Save the last frame of `path` as a png, or return None if it is not a video.

    Used as the style anchor for later Sora clips: the closing frame of the first clip
    is what the next scene should still look like.
    """
    if not check_if_video(path):
        return None

    frame_path = f"{dir_name}{uuid.uuid4()}.png"
    try:
        with VideoFileClip(path) as clip:
            for t in (clip.duration - 0.5, clip.duration * 0.5, 0):
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


def create_image_scene(
    prompt: str,
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
    scene = Scene.objects.get(prompt=prompt, text=text.strip())
    generate = resolve(mode, provider)

    if generate is None:
        logger.error("No image provider for mode %s and provider %s", mode, provider)
        downloaded_image = None
    else:
        try:
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
    reference = None
    for scene in video.gpt_answer["scenes"]:
        for sentence in scene["sentences"]:
            produced = create_image_scene(
                prompt=video.prompt,
                image=sentence["image_description"],
                text=scene_text(sentence),
                dir_name=dir_name,
                mode=mode,
                style=style,
                title=video.title,
                provider=provider,
                reference=reference,
                with_audio=with_audio,
                user=video.created_by,
            )

            if reference is None and produced:
                reference = still_from_video(produced, f"{dir_name}/images/")


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
    generate = resolve(video.mode)

    if generate is None:
        logger.error(f"Invalid video mode or provider not found for video {video.id}.")
        return scene_image

    try:
        img = generate(
            scene_image.prompt,
            f"{video.dir_name}/images/",
            style=style,
            title=video.title,
            user=video.created_by,
            *args,
            **kwargs,
        )

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

    curr_scene = Scene.objects.create(prompt=prompt, text=title, is_last=True)

    SceneImage.objects.create(
        scene=curr_scene, file=edited_video, prompt="twitch video", with_audio=True
    )
