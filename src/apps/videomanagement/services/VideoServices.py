import logging
import os
from rest_framework.exceptions import APIException

from django.db import transaction

from ..models import Videos, Avatars, Scene, SceneImage, Intro, Outro
from ..utils.audio_utils import update_scene
from ..utils.visual_utils import generate_new_image

logger = logging.getLogger(__name__)


def video_update(video: Videos,
                 title: str = None,
                 avatar: str = None,
                 intro: str = None,
                 outro: str = None,
                 subtitles: bool = False,
                 avatar_position: str = "right,top"
                 ) -> Videos:
    """
    Update the specified video with new avatar, intro, or outro.

    Args:
        video (Videos): The video instance to update.
        title (str, optional): The title of the video
        avatar (str, optional): The ID of the new avatar or "no_value" to remove the avatar. Defaults to None.
        intro (str, optional): The ID of the new intro or "no_value" to remove the intro. Defaults to None.
        outro (str, optional): The ID of the new outro or "no_value" to remove the outro. Defaults to None.
        subtitles (bool, optional): If you want subs or not
        avatar_position (str, optional): Where the avatar should be located

    Returns:
        Videos: The updated video instance.
    """

    video.title = title

    if avatar == "null" or avatar == '' or not avatar or video.video_type == "TWITCH":
        video.avatar = None

    else:

        selected_avatar = Avatars.objects.get(id = avatar)
        video.avatar = selected_avatar

        if video.voice_model != selected_avatar.voice:
            video.voice_model = selected_avatar.voice
            video.save()
            scenes = Scene.objects.filter(prompt = video.prompt)
            for scene in scenes:
                update_scene(scene)

    try:
        video.intro = Intro.objects.get(id = intro) if intro != "null" and intro != '' else None
    except Intro.DoesNotExist:
        raise APIException("Intro with that id does not Exists !")

    try:
        video.outro = Outro.objects.get(id = outro) if outro != "null" and outro != '' else None
    except Outro.DoesNotExist:
        raise APIException("Outro with that id does not Exists !")

    if video.video_type != 'TWITCH':
        video.settings = dict(subtitles = subtitles == 'true', avatar_position = avatar_position)

    video.save()

    return video


def video_regenerate(video: Videos) -> int:
    with transaction.atomic():

        for scene in Scene.objects.filter(prompt = video.prompt):
            update_scene(scene)
            scenes_images = SceneImage.objects.filter(scene = scene)

            for scene_image in scenes_images:
                generate_new_image(scene_image = scene_image, video = video)

        if video.avatar and os.path.exists(rf'{os.getcwd()}\{video.dir_name}\output_avatar.mp4'):
            os.remove(rf'{os.getcwd()}\{video.dir_name}\output_avatar.mp4')

        video.status = "READY"
        video.save()


