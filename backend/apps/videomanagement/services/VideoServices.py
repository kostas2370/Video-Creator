import logging
from .asset_selection import owned_asset


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

    selected_avatar = (
        None if video.video_type == VideoType.TWITCH
        else owned_asset(Avatar, avatar, video.created_by)
    )
    selected_intro = owned_asset(Intro, intro, video.created_by)
    selected_outro = owned_asset(Outro, outro, video.created_by)

    if title:
        video.title = title
    video.avatar = selected_avatar
    video.intro = selected_intro
    video.outro = selected_outro

    if selected_avatar and video.voice_model != selected_avatar.voice:
        video.voice_model = selected_avatar.voice
        video.save()
        for scene in video.scenes.all():
            update_scene(scene)

    if video.video_type != VideoType.TWITCH:
        video.settings = dict(subtitles=subtitles, avatar_position=avatar_position)

    video.save()

    return video
