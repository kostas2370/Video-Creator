import logging

from django.conf import settings
from moviepy.editor import (
    AudioFileClip,
    concatenate_audioclips,
    CompositeAudioClip,
    ImageClip,
    VideoFileClip,
    vfx,
)

from ...models import SceneImage, Background, Scene
from ..file_utils import check_if_image, check_if_video

logger = logging.getLogger(__name__)


def clip_audio(scene_image: SceneImage):
    """
    The scene visual's own soundtrack, for a video clip that is meant to be heard.

    Returns None for a still, for a clip flagged silent, or when the file carries no
    audio track at all.
    """
    if not scene_image or not scene_image.with_audio or not scene_image.file:
        return None

    try:
        return VideoFileClip(scene_image.file.path).audio

    except Exception as e:
        logger.error(f"Error processing scene image audio: {e}")
        return None


def handle_audio(scene: Scene, scene_image: SceneImage):
    """
    Processes and returns the appropriate audio clip based on the given scene and scene image.

    Args:
        scene (Scene): The scene object containing metadata and file path for the audio.
        scene_image (SceneImage): The scene image object containing the file path and an indicator if it includes audio.

    Returns:
        AudioFileClip: The processed audio clip for the scene, which may be a combination of the scene's audio,
                       the scene image's audio, and silence if applicable.
    """

    audio = None

    if scene.file:
        try:
            audio = AudioFileClip(scene.file.path)
        except Exception as e:
            logger.error(f"Error loading scene audio: {e}")

    scene_audio = clip_audio(scene_image)
    if scene_audio is not None:
        audio = CompositeAudioClip([audio, scene_audio]) if audio else scene_audio

    if scene_image and scene.is_last and not scene_image.with_audio and audio:
        return concatenate_audioclips(
            [
                audio,
                AudioFileClip("assets/blank.wav"),
                AudioFileClip("assets/blank.wav"),
            ]
        )

    if audio is None:
        return AudioFileClip("assets/blank.wav")

    return audio


def handle_image(audio, scene_image, background):
    """
    Processes and returns the appropriate image clip based on the given audio and scene image.

    Args:
        audio (AudioFileClip): The audio clip associated with the scene.
        scene_image (SceneImage): The scene image object containing the file path.
        background (Background): A background object that contains a file of the background image.


    Returns:
        ImageClip: The processed image clip for the scene, which may include resizing, duration adjustment,
                   and fade effects, or a default black image clip in case of an error.
    """
    try:
        image = ImageClip(scene_image.file.path)

        if background:
            w, h = ImageClip(background.file.path).size
            image = image.resize((int(w * 0.65), int(h * 0.65)))

        image = image.set_duration(
            audio.duration if audio else settings.SILENT_SCENE_SECONDS
        )
        image = image.fadein(image.duration * 0.2).fadeout(image.duration * 0.2)
    except Exception as exc:
        raise Exception(f"Error handling image: {exc}")

    return image


def handle_video(audio: AudioFileClip, scene_image: SceneImage) -> VideoFileClip:
    """
    Processes and returns the appropriate video clip based on the given audio and scene image.

    Args:
        audio (AudioFileClip): The audio clip associated with the scene.
        scene_image (SceneImage): The scene image object containing the file path to the video file.

    Returns:
        VideoFileClip: The processed video clip for the scene, which includes duration adjustment and fade effects.
    """
    try:
        vid_scene = VideoFileClip(scene_image.file.path).without_audio()

    except Exception as e:
        raise ValueError(f"Error loading video file at {scene_image.file.path}: {e}")

    if audio is not None:
        if vid_scene.duration > audio.duration:
            vid_scene = vid_scene.subclip(0, audio.duration)

        elif vid_scene.duration < audio.duration:
            vid_scene = vid_scene.fx(
                vfx.freeze, t="end", total_duration=audio.duration
            ).set_duration(audio.duration)

    vid_scene = vid_scene.fadein(vid_scene.duration * 0.2).fadeout(
        vid_scene.duration * 0.2
    )
    return vid_scene


def process_scene(scene_image: SceneImage, audio, background: Background):
    """
    Processes and returns the appropriate visual clip (image or video) based on the given scene image and audio.

    This function handles the scene by:
    1. Creating a default black video clip with the duration of the audio.
    2. Checking if the scene image is an image or a video.
    3. Processing the scene image as an image or video accordingly.
    4. Returning the processed visual clip.

    Args:
        scene_image (SceneImage): The scene image object containing the file path to the image or video file.
        audio (AudioFileClip): The audio clip associated with the scene.
        background (bool): A flag indicating if the image should be resized as a background.

    Returns:
        VideoFileClip: The processed visual clip for the scene, which may be a black video, an image clip,
                       or a video clip based on the scene image file type.
    """
    black_clip = ImageClip("assets/black.jpg").set_duration(
        audio.duration if audio else settings.SILENT_SCENE_SECONDS
    )

    if not scene_image or not scene_image.file:
        return black_clip

    file_path = scene_image.file.path

    try:
        if check_if_image(file_path):
            return handle_image(audio, scene_image, background)

        if check_if_video(file_path):
            return handle_video(audio, scene_image)

    except Exception as exc:
        logger.warning(exc)

    logger.warning(
        f"Warning: Unsupported file type for {file_path}. Returning black clip."
    )

    return black_clip
