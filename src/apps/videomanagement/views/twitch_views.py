from rest_framework.response import Response
from slugify import slugify
from rest_framework.decorators import api_view

from drf_yasg.utils import swagger_auto_schema
from datetime import date

from ..utils.download_utils import create_twitch_clip_scene

from ..utils.twitch import TwitchClient

from ..utils.file_utils import generate_directory
from ..serializers import VideoSerializer
from ..models import Videos, UserPrompt, Intro, Outro

from ..swagger_serializers import TwitchSerializer


@swagger_auto_schema(operation_description = "generates a video from twitch clips, depending on the game or streamer",
                     method = "POST",
                     request_body = TwitchSerializer)
@api_view(['POST'])
def generate_twitch(request):
    mode = request.data.get('mode', 'game')
    value = request.data.get('value')
    amt = request.data.get('amt', 10)
    started_at = request.data.get('started_at', "")

    message = f"Mode : {mode} Value : {value}"
    title = f"{request.data.get('value')} {date.today()}"
    dir_name = generate_directory(rf'media\videos\{slugify(title)}')

    userprompt = UserPrompt.objects.create(template = None, prompt = f'{message}')

    intro = Intro.objects.filter(category= "GAMING").first()
    outro = Outro.objects.filter(category= "GAMING").first()

    video = Videos.objects.create(prompt = userprompt,
                                  dir_name = dir_name,
                                  title = title,
                                  intro = intro,
                                  outro = outro)

    client = TwitchClient(path = dir_name)
    client.set_headers()

    value = client.get_streamer_id(value) if mode == "streamer" else client.get_game_id(value)
    clips = client.get_clips(value, mode, started_at)

    description = "Source : \n"
    for count, clip in enumerate(clips[:amt]):
        downloaded_clip = client.download_clip(clip)
        create_twitch_clip_scene(downloaded_clip, clip.get("title"), video.prompt)
        description += f"{count+1} {clip.get('title')} : {clip.get('url')} \n"

    video.gpt_answer = description
    video.save()

    return Response(VideoSerializer(video).data)
