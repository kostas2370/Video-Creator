from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework.decorators import api_view

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from ..utils.download_utils import download_playlist

from ..serializers import TemplatePromptsSerializer, MusicSerializer, AvatarNestedSerializer, VoiceModelSerializer, \
    AvatarSerializer, SceneImageSerializer
from ..models import TemplatePrompts, Music, VoiceModels, Avatars, SceneImage

from ..swagger_serializers import DownloadPlaylistSerializer


swagger_video_id = openapi.Parameter('video_id', openapi.IN_QUERY, description="Id of the video",
                                     type=openapi.TYPE_NUMBER)
swagger_images = openapi.Parameter('images', openapi.IN_QUERY, description="Image mode , webscrap or AI",
                                   type=openapi.TYPE_STRING)
swagger_style = openapi.Parameter('image_style', openapi.IN_QUERY, description="DALL E image styles ; vivid, natural",
                                  type=openapi.TYPE_STRING)


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



