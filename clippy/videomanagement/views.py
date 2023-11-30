from rest_framework.response import Response
from slugify import slugify
from rest_framework.permissions import AllowAny
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes

from .utils.video_utils import make_video
from .utils.download_utils import download_playlist, create_image_scenes
from .utils.prompt_utils import format_prompt
from .utils.gpt_utils import get_reply
from .utils.audio_utils import make_scenes_speech
from .utils.file_utils import generate_directory, select_avatar, select_voice
from .serializers import TemplatePromptsSerializer, MusicSerializer, VideoSerializer
from .models import TemplatePrompts, Music, Videos, VoiceModels, UserPrompt, Avatars


class TemplatePromptView(viewsets.ModelViewSet):
    serializer_class = TemplatePromptsSerializer
    queryset = TemplatePrompts.objects.all()
    permission_classes = [AllowAny]


class MusicView(viewsets.ModelViewSet):
    serializer_class = MusicSerializer
    queryset = Music.objects.all()
    permission_classes = [AllowAny]


class VideoView(viewsets.ModelViewSet):
    serializer_class = VideoSerializer
    queryset = Videos.objects.all()
    permission_classes = [AllowAny]


class TestView(viewsets.ModelViewSet):
    serializer_class = TemplatePromptsSerializer
    queryset = TemplatePrompts.objects.all()
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        template_id = request.data.get('template_id', 2)
        voice_id = request.data.get('voice_id', None)
        title = request.data.get('title')
        prompt = request.data.get('prompt')
        gpt_model = request.data.get('gpt_model', 'gpt-3.5-turbo')
        image_webscrap = request.data.get('image_webscrap', False)
        avatar = request.data.get('avatar', False)
        avatar_selection = request.data.get('avatar_selection', 'random')

        # target_audience = request.data.get('target_audience')

        template = TemplatePrompts.objects.get(id = template_id)

        message = format_prompt(template, userprompt = prompt, title = title)

        userprompt = UserPrompt.objects.create(template = template, prompt = message)
        userprompt.save()

        vid = Videos.objects.create(title = title, prompt = userprompt)

        x = get_reply(message, gpt_model = gpt_model)
        vid.gpt_answer = x

        dir_name = generate_directory(rf'media\media\videos\{slugify(x["title"])}')
        vid.dir_name = dir_name

        if type(avatar) is int:
            avatar = select_avatar(selected = avatar)
            voice_model = avatar.voice

        elif avatar is True:
            avatar = select_avatar()
            voice_model = avatar.voice

        elif voice_id is not None:
            voice_model = VoiceModels.objects.get(id = voice_id)

        else:
            voice_model = select_voice()

        vid.voice_model = voice_model

        make_scenes_speech(vid)

        if image_webscrap:
            create_image_scenes(vid)

        vid.save()

        result = make_video(vid, avatar = avatar, avatar_selection = avatar_selection)

        return Response({"message": "The video has been made successfully",
                         "result": VideoSerializer(result).data})


@api_view(['POST'])
@permission_classes([AllowAny])
def download_playlist(request):
    link = request.data['link']
    download_playlist(link, category = request.data.get('category'))
    return Response({'Message': 'Successful'})

@api_view(['POST'])
@permission_classes([AllowAny])
def render_video(request):
    vid = Videos.objects.get(id = request.data['video_id'])

    result = make_video(vid, avatar = True)
    return Response({"message": "The video has been made successfully", "result": VideoSerializer(result).data})



