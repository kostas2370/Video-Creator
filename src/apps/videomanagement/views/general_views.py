from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.filters import OrderingFilter, SearchFilter

from django_filters.rest_framework import DjangoFilterBackend


from ..models import TemplatePrompts, Outro, Intro, Music, VoiceModels, Avatars, SceneImage, Videos
from ..serializers import TemplatePromptsSerializer, IntroSerializer, OutroSerializer, MusicSerializer, \
    AvatarNestedSerializer, VoiceModelSerializer, AvatarSerializer, SceneImageSerializer
from ..swagger_serializers import DownloadPlaylistSerializer
from ..utils.visual_utils import download_playlist


class SceneImageView(viewsets.ModelViewSet):
    queryset = SceneImage.objects.all()
    serializer_class = SceneImageSerializer

    def destroy(self, request, pk):
        obj = self.get_object()
        video = Videos.objects.get(prompt=obj.scene.prompt)
        if video.video_type == "AI":
            obj.file = None
            obj.save()

        if video.video_type == "TWITCH":
            obj.scene.delete()

        return Response({"message": "scene image deleted !"}, status = 204)


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
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name']

    serializer_class = AvatarSerializer
    queryset = Avatars.objects.all()


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
