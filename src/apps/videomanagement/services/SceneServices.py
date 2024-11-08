from rest_framework.exceptions import APIException
import logging

from ..models import Scene, Videos, SceneImage
from ..swagger_serializers import AddSceneSerializer
from ..utils.audio_utils import update_scene as update
from ..utils.gpt_utils import get_update_sentence
from ..utils.prompt_utils import format_update_form
from ..utils.twitch import TwitchClient
from ..utils.visual_utils import create_twitch_clip_scene, create_image_scene
from ..utils.audio_utils import make_scene_speech, get_syn

logger = logging.getLogger(__name__)


def generate_scene(text: str,
                   scene: Scene) -> str:
    """
    Generate an updated version of the scene text and update the scene with it.

    Args:
        text (str): The new text for the scene.
        scene (Scene): The scene instance to update.

    Returns:
        str: The updated text for the scene.
    """

    if text == scene.text.strip():
        return text

    text = get_update_sentence(format_update_form(scene.text, text))

    return text


def update_scene(text: str, scene: Scene):
    """
    Update the text of a scene with new content.

    Args:
        text (str): The new text content for the scene.
        scene (Scene): The scene object to update.

    Returns:
        str: The updated text content of the scene.
    """
    new_text = text
    scene.text = new_text if new_text else scene.text
    update(scene)
    return scene.text


def create_scene(video: Videos, data: dict, files: dict) -> Scene:
    data = data.copy()
    data["mode"] = video.video_type
    serializer = AddSceneSerializer(data = data)
    serializer.is_valid(raise_exception = True)
    scene = None

    if video.video_type == "TWITCH":
        client = TwitchClient(video.dir_name)
        client.set_headers()
        try:
            clip = client.get_clip_by_url(serializer.data.get("url"))
            downloaded_clip = client.download_clip(clip[0])
            create_twitch_clip_scene(downloaded_clip, clip[0].get("title"), video.prompt)

        except Exception as esc:
            raise APIException(str(esc), code= 400)

    if video.video_type == "AI":
        try:
            scene = make_scene_speech(video.voice_model, video.dir_name, video.prompt, serializer.data["text"],
                                      serializer.data['is_last'])

        except Exception as exc:
            logger.error(exc)
            raise APIException(str(exc), code= 400)

        if files.get('image'):
            SceneImage.objects.create(scene = scene, file = files['image'],
                                      prompt = serializer.data.get('image_description', ""),
                                      with_audio = serializer.data['with_audio'], )

        if serializer.data.get("image_description"):
            create_image_scene(prompt = video.prompt, image = serializer.data['image_description'], text = scene.text,
                               dir_name = video.dir_name, mode = video.mode, title = video.title)

    return scene
