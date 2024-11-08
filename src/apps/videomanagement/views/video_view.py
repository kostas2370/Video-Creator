import logging

from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action, throttle_classes
from rest_framework.response import Response
from rest_framework.filters import OrderingFilter, SearchFilter

from rest_framework.permissions import IsAuthenticated

from ..models import Videos, SceneImage
from ..paginator import StandardResultsSetPagination
from ..swagger_serializers import VideoUpdateSerializer, AddSceneSerializer
from ..serializers import VideoSerializer, VideoNestedSerializer, SceneSerializer
from ..services.VideoServices import video_update, video_regenerate
from ..services.SceneServices import create_scene
from ..utils.video_utils import make_video
from ..throttling import RenderRateThrottle
from ..permissions import IsOwnerPermission
logger = logging.getLogger(__name__)


class VideoView(viewsets.ModelViewSet):
    serializer_class = VideoSerializer
    queryset = Videos.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['title']
    permission_classes = [IsAuthenticated, IsOwnerPermission]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):

        return Videos.objects.filter(~Q(gpt_answer=None), created_by_id=self.request.user.id).order_by("-id").\
            select_related("music", "prompt")

    def get_serializer_class(self):
        serializer_class = {
            "retrieve": VideoNestedSerializer,
            "partial_update": VideoUpdateSerializer,
            "add_scene": AddSceneSerializer
        }

        return serializer_class.get(self.action, VideoSerializer)

    @swagger_auto_schema(request_body = VideoUpdateSerializer,
                         operation_description = "This API updates the attributes of the video. If you add a new avatar"
                                                 " it will delete previous audio files and will regenerate them with "
                                                 "new audios")
    def partial_update(self, request, pk):
        serializer = self.get_serializer(data = request.data)
        serializer.is_valid(raise_exception = True)
        video = self.get_object()
        outcome = video_update(video, **serializer.validated_data)
        logger.info(f"Video with id {pk}  got updated successfully")
        return Response({"message": "Updated Success",
                         "video": VideoNestedSerializer(outcome).data})

    @swagger_auto_schema(operation_description = "This api changes the image of the scene or it creates "
                                                 "a new one if it doesnt exists", method = "GET")
    @action(detail = True, methods = ["GET"])
    def video_regenerate(self, _, pk):
        video = self.get_object()
        video.status = "GENERATION"
        video.save()
        video_regenerate(video)
        logger.info(f"Video with id {pk}  got regenerated successfully")

        return Response({"Message": f"Video with id {pk} got regenerated successfully"}, status = status.HTTP_200_OK)

    @swagger_auto_schema(operation_description = "This api renders the video, you will have to put a query param in url"
                                                 " video_id with the video you wanna render", method = "PATCH")
    @action(detail = True, methods = ["PATCH"])
    @throttle_classes([RenderRateThrottle])
    def render_video(self, _, pk):
        vid = self.get_object()
        try:
            result = make_video(vid)
            return Response({"message": "The video has been made successfully",
                             "result": self.get_serializer(result).data})

        except Exception as exc:
            logger.error(exc)
            vid.status = "FAILED"
            vid.save()

        return Response({"message": "The render failed, probably you have to generate a new one"}, status = 400)

    @swagger_auto_schema(operation_description = "This api add a scene to the video", method = "POST",
                         request_body = AddSceneSerializer)
    @action(detail = True, methods = ["POST"])
    def add_scene(self, request, pk):

        scene = create_scene(video = self.get_object(),
                             data = request.data,
                             files = request.FILES)

        return Response({"message": "The scene was added successfully",
                         "scene": SceneSerializer(scene).data}, status = 200)


