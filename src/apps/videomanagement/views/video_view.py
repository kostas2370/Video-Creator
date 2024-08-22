import logging

from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import OrderingFilter,SearchFilter

from ..models import Videos
from ..paginator import StandardResultsSetPagination
from ..serializers import VideoSerializer, VideoNestedSerializer
from ..services.VideoServices import video_update, video_regenerate
from ..utils.video_utils import make_video

logger = logging.getLogger(__name__)


class VideoView(viewsets.ModelViewSet):
    serializer_class = VideoSerializer
    queryset = Videos.objects.filter(~Q(gpt_answer=None)).order_by("-id")
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['title']
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        if self.action == "retrieve":
            return VideoNestedSerializer

        return VideoSerializer

    @swagger_auto_schema(request_body = VideoSerializer,
                         operation_description = "This API updates the attributes of the video. If you add a new avatar"
                                                 " it will delete previous audio files and will regenerate them with "
                                                 "new audios")
    def partial_update(self, request, pk):
        avatar = request.data.get('avatar')
        intro = request.data.get('intro')
        outro = request.data.get('outro')
        title = request.data.get("title")

        video = self.get_object()

        outcome = video_update(video, title, avatar, intro, outro)
        logger.info(f"Video with id {pk}  got updated successfully")
        return Response({"message": "Updated Success",
                         "video": self.get_serializer_class()(outcome).data})

    @swagger_auto_schema(operation_description = "This api changes the image of the scene or it creates "
                                                 "a new one if it doesnt exists", method = "GET")
    @action(detail = True, methods = ["GET"])
    def video_regenerate(self, _, pk):

        if pk is None:
            logger.warning(f"Tried to regenerate without a pk")

            return Response({'Message': "You must insert a video_id"}, status = status.HTTP_400_BAD_REQUEST)

        video = get_object_or_404(Videos, id = pk)
        video.status = "GENERATION"
        video.save()
        video_regenerate(video)
        logger.info(f"Video with id {pk}  got regenerated successfully")

        return Response({"Message": f"Video with id {pk} got regenerated successfully"}, status = status.HTTP_200_OK)

    @swagger_auto_schema(operation_description = "This api renders the video, you will have to put a query param in url"
                                                 " video_id with the video you wanna render", method = "PATCH")
    @action(detail = True, methods = ["PATCH"])
    def render_video(self, _, pk):
        vid = Videos.objects.get(id = pk)
        try:
            result = make_video(vid)
            return Response({"message": "The video has been made successfully", "result": VideoSerializer(result).data})

        except Exception as exc:
            logger.error(exc)
            vid.status = "FAILED"
            vid.save()

        return Response({"message": "The render failed, probably you have to generate a new one"}, status = 400)
