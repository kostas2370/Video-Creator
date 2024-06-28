from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..models import TemplatePrompts, Outro, Intro, Music, VoiceModels, Avatars, SceneImage
from ..serializers import TemplatePromptsSerializer, IntroSerializer, OutroSerializer, MusicSerializer, \
    AvatarNestedSerializer, VoiceModelSerializer, AvatarSerializer, SceneImageSerializer
from ..swagger_serializers import DownloadPlaylistSerializer
from ..utils.visual_utils import download_playlist


class SceneImageView(viewsets.ModelViewSet):
    queryset = SceneImage.objects.all()
    serializer_class = SceneImageSerializer


class TemplatePromptView(viewsets.ModelViewSet):
    serializer_class = TemplatePromptsSerializer
    queryset = TemplatePrompts.objects.all()


class MusicView(viewsets.ModelViewSet):
    serializer_class = MusicSerializer
    queryset = Music.objects.all()


class VoiceView(viewsets.ModelViewSet):
    serializer_class = VoiceModelSerializer
    queryset = VoiceModels.objects.all()


class AvatarView(viewsets.ModelViewSet):
    serializer_class = AvatarSerializer
    queryset = Avatars.objects.all()

    def get_serializer_class(self):
        if self.action == "list":
            return AvatarNestedSerializer

        return AvatarSerializer


class IntroView(viewsets.ModelViewSet):
    serializer_class = IntroSerializer
    queryset = Intro.objects.all()


class OutroView(viewsets.ModelViewSet):
    serializer_class = OutroSerializer
    queryset = Outro.objects.all()


@swagger_auto_schema(request_body = DownloadPlaylistSerializer,
                     operation_description = "This API downloads music playlist. The required fields are :"
                                             " Category and URL ",
                     method = "POST")
@api_view(['POST'])
def download_playlist(request):
    DownloadPlaylistSerializer(data = request.data).is_valid(raise_exception = True)
    link = request.data['link']
    download_playlist(link, category = request.data.get('category'))
    return Response({'Message': 'Successful'})
