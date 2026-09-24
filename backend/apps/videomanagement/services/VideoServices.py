import logging
from rest_framework.exceptions import APIException


from ..models import Video, VideoType, Avatar, Intro, Outro
from ..utils.audio_utils import update_scene

logger = logging.getLogger(__name__)


def video_update(
    video: Video,
    title: str = None,
    avatar: str = None,
    intro: str = None,
    outro: str = None,
    subtitles: bool = False,
    avatar_position: str = "right,top",
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

    if title:
        video.title = title

    if video.video_type == VideoType.TWITCH or avatar in (None, "", "None"):
        video.avatar = None

    else:
        selected_avatar = Avatar.objects.get(id=avatar)
        video.avatar = selected_avatar

        if video.voice_model != selected_avatar.voice:
            video.voice_model = selected_avatar.voice
            video.save()
            scenes = video.scenes.all()
            for scene in scenes:
                update_scene(scene)
    try:
        video.intro = (
            None if intro in (None, "", "null") else Intro.objects.get(id=intro)
        )
    except Intro.DoesNotExist:
        raise APIException("Intro with that id does not Exists !")

    try:
        video.outro = (
            None if outro in (None, "", "null") else Outro.objects.get(id=outro)
        )
    except Outro.DoesNotExist:
        raise APIException("Outro with that id does not Exists !")

    if video.video_type != VideoType.TWITCH:
        video.settings = dict(subtitles=subtitles, avatar_position=avatar_position)

    video.save()

    return video
