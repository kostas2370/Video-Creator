import logging

from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action, throttle_classes
from rest_framework.response import Response
from rest_framework.filters import OrderingFilter, SearchFilter

from rest_framework.permissions import IsAuthenticated

from ..models import Video
from ..paginator import StandardResultsSetPagination
from ..swagger_serializers import VideoUpdateSerializer, AddSceneSerializer
from ..serializers import VideoSerializer, VideoNestedSerializer, SceneSerializer
from ..services.VideoServices import video_update
from ..services.SceneServices import create_scene
from ..tasks import regenerate_video_task, render_video_task
from ..throttling import RenderRateThrottle
from ..permissions import IsOwnerPermission

logger = logging.getLogger(__name__)


class VideoView(viewsets.ModelViewSet):
    serializer_class = VideoSerializer
    queryset = Video.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["title"]
    # DjangoFilterBackend was enabled but had no fields to act on. Status is what a
    # client needs now that videos are visible while a worker is still on them.
    filterset_fields = ["status", "video_type"]
    permission_classes = [IsAuthenticated, IsOwnerPermission]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = (
            Video.objects.filter(created_by_id=self.request.user.id)
            .order_by("-id")
            .select_related("music", "prompt")
        )

        # Detail routes have to reach a video the moment it exists, so a client can
        # poll it while a worker is still filling it in. The list keeps its old
        # behaviour of hiding videos that have no gpt_answer yet.
        if self.action == "list":
            queryset = queryset.exclude(gpt_answer=None)

        return queryset

    def get_serializer_class(self):
        serializer_class = {
            "retrieve": VideoNestedSerializer,
            "partial_update": VideoUpdateSerializer,
            "add_scene": AddSceneSerializer,
        }

        return serializer_class.get(self.action, VideoSerializer)

    @swagger_auto_schema(
        request_body=VideoUpdateSerializer,
        operation_description="This API updates the attributes of the video. If you add a new avatar"
        " it will delete previous audio files and will regenerate them with "
        "new audios",
    )
    def partial_update(self, request, pk):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        video = self.get_object()
        outcome = video_update(video, **serializer.validated_data)
        logger.info(f"Video with id {pk}  got updated successfully")
        return Response(
            {"message": "Updated Success", "video": VideoNestedSerializer(outcome).data}
        )

    @swagger_auto_schema(
        operation_description="Queues regeneration of the scene audio and imagery. Returns 202; "
        "poll GET /video/{id}/ until its status becomes READY or FAILED.",
        method="PATCH",
    )
    @action(detail=True, methods=["PATCH"])
    def video_regenerate(self, _, pk):
        video = self.get_object()
        video.status = "GENERATION"
        video.save()
        regenerate_video_task.delay(video_id=video.id)
        logger.info(f"Video with id {pk} was queued for regeneration")

        return Response(
            {
                # "Message" is the key this endpoint has always returned; kept so an
                # existing client's toast does not go blank.
                "Message": f"Video with id {pk} was queued for regeneration",
                "message": f"Video with id {pk} was queued for regeneration",
                "video": VideoSerializer(video).data,
            },
            status=status.HTTP_202_ACCEPTED,
        )

    @swagger_auto_schema(
        operation_description="Queues the render of the video. Returns 202; poll GET /video/{id}/ "
        "until its status becomes COMPLETED or FAILED, then read `output`.",
        method="PATCH",
    )
    @action(detail=True, methods=["PATCH"])
    @throttle_classes([RenderRateThrottle])
    def render_video(self, _, pk):
        vid = self.get_object()

        if vid.status not in {"READY", "COMPLETED"}:
            return Response(
                {
                    "message": f"Video with id {pk} is {vid.status} and cannot be rendered yet"
                },
                status=status.HTTP_409_CONFLICT,
            )

        render_video_task.delay(video_id=vid.id)
        logger.info(f"Video with id {pk} was queued for rendering")

        return Response(
            {
                "message": "The render has been queued",
                "video": VideoSerializer(vid).data,
            },
            status=status.HTTP_202_ACCEPTED,
        )

    @swagger_auto_schema(
        operation_description="This api add a scene to the video",
        method="POST",
        request_body=AddSceneSerializer,
    )
    @action(detail=True, methods=["POST"])
    def add_scene(self, request, pk):
        scene = create_scene(
            video=self.get_object(), data=request.data, files=request.FILES
        )

        return Response(
            {
                "message": "The scene was added successfully",
                "scene": SceneSerializer(scene).data,
            },
            status=200,
        )
