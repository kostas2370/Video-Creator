import logging
import os
from rest_framework.exceptions import APIException

from django.db import transaction

from ..models import Video, Avatar, Intro, Outro
from ..utils.audio_utils import update_scene
from ..utils.visual_utils import generate_new_image

logger = logging.getLogger(__name__)


def video_update(video: Video,
                 title: str = None,
                 avatar: str = None,
                 intro: str = None,
                 outro: str = None,
                 subtitles: bool = False,
                 avatar_position: str = "right,top"
                 ) -> Video:
    """
    Update the specified video with new avatar, intro, or outro.

    Args:
        video (Videos): The video instance to update.
        title (str, optional): The title of the video
        avatar (str, optional): The ID of the new avatar or "no_value" to remove the avatar. Defaults to None.
        intro (str, optional): The ID of the new intro or "no_value" to remove the intro. Defaults to None.
        outro (str, optional): The ID of the new outro or "no_value" to remove the outro. Defaults to None.
        subtitles (bool, optional): Boolean value that shows if the video will have subtitles or not.
        avatar_position(str, optional): A string with 'right,top' that shows where the avatar will be placed."
    Returns:
        Videos: The updated video instance.
    """

    video.title = title

    if avatar == "None" or avatar == '' or video.video_type == "TWITCH" or avatar is None:
        video.avatar = None

    else:
        print(avatar)
        selected_avatar = Avatar.objects.get(id = avatar)
        video.avatar = selected_avatar

        if video.voice_model != selected_avatar.voice:
            video.voice_model = selected_avatar.voice
            video.save()
            scenes = video.prompt.scenes.all()
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


def video_regenerate(video: Video) -> None:
    with transaction.atomic():
        for scene in video.prompt.scenes.all():
            update_scene(scene)

            for scene_image in scene.scene_images.all():
                generate_new_image(scene_image = scene_image, video = video)

        if video.avatar and os.path.exists(rf'{os.getcwd()}\{video.dir_name}\output_avatar.mp4'):
            os.remove(rf'{os.getcwd()}\{video.dir_name}\output_avatar.mp4')

        video.status = "READY"
        video.save()
