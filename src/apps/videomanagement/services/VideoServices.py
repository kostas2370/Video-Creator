from django.db import transaction
import os
from ..utils.audio_utils import update_scene
from ..models import Videos, Avatars, Scene, SceneImage, Intro, Outro
from ..utils.visual_utils import generate_new_image

import logging


logger = logging.getLogger(__name__)


def video_update(video: Videos,
                 avatar: str = None,
                 intro: str = None,
                 outro: str = None,
                 ) -> Videos:
    """
    Update the specified video with new avatar, intro, or outro.

    Args:
        video (Videos): The video instance to update.
        avatar (str, optional): The ID of the new avatar or "no_value" to remove the avatar. Defaults to None.
        intro (str, optional): The ID of the new intro or "no_value" to remove the intro. Defaults to None.
        outro (str, optional): The ID of the new outro or "no_value" to remove the outro. Defaults to None.

    Returns:
        Videos: The updated video instance.
    """

    if avatar and avatar == "no_value":
        video.avatar = None

    elif avatar and type(avatar) is str:
        selected_avatar = Avatars.objects.get(id = avatar)
        video.avatar = selected_avatar

        if video.voice_model != selected_avatar.voice:
            video.voice_model = selected_avatar.voice
            video.save()
            scenes = Scene.objects.filter(prompt = video.prompt)
            for scene in scenes:
                update_scene(scene)

    if intro:
        intro = Intro.objects.get(
            id = intro) if intro is not None and intro != "no_value" else None if intro == "no_value" else video.intro

    if outro:
        outro = Outro.objects.get(
            id = outro) if outro is not None and outro != "no_value" else None if outro == "no_value" else video.outro

    video.intro = intro
    video.outro = outro
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


