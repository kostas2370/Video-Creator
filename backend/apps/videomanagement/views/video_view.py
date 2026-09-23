import logging

from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import OrderingFilter, SearchFilter

from rest_framework.permissions import IsAuthenticated

from ..models import Video
from ..paginator import StandardResultsSetPagination
from ..swagger_serializers import VideoUpdateSerializer, AddSceneSerializer
from ..serializers import VideoSerializer, VideoNestedSerializer, SceneSerializer
from ..services.VideoServices import video_update
from ..services.SceneServices import create_scene
from ..tasks import render_video_task, resume_video_task
from ..throttling import RenderRateThrottle, ResumeRateThrottle
from ..permissions import AiGenerationLimitPermission, IsOwnerPermission

logger = logging.getLogger(__name__)


class VideoView(viewsets.ModelViewSet):
    serializer_class = VideoSerializer
    queryset = Video.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["title"]
    filterset_fields = ["status", "video_type"]
    permission_classes = [IsAuthenticated, IsOwnerPermission]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = (
            Video.objects.filter(created_by_id=self.request.user.id)
            .order_by("-id")
            .select_related("music", "prompt")
        )
        if self.action == "list":
            queryset = queryset.exclude(gpt_answer__isnull=True)

        if self.action == "retrieve":
            queryset = queryset.prefetch_related("scenes__scene_images")

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
        operation_description="Queues the unfinished part of a generation that stopped "
        "early. Only the scenes with no narration and the sentences with no visual are "
        "worked on again, so nothing already produced is paid for twice. Returns 202; "
        "poll GET /video/{id}/ until its status becomes READY or FAILED.",
        method="PATCH",
    )
    @action(
        detail=True,
        methods=["PATCH"],
        throttle_classes=[ResumeRateThrottle],
        permission_classes=[
            IsAuthenticated,
            IsOwnerPermission,
            AiGenerationLimitPermission,
        ],
    )
    def resume(self, _, pk):
        video = self.get_object()

        if not video.gpt_answer or not video.dir_name:
            return Response(
                {
                    "message": f"Video with id {pk} never got a script, so there is "
                    "nothing to carry on from. Generate it again."
                },
                status=status.HTTP_409_CONFLICT,
            )

        claimed = Video.objects.filter(
            pk=video.pk, status__in=["FAILED", "READY"]
        ).update(status="GENERATION")

        if not claimed:
            video.refresh_from_db()
            return Response(
                {
                    "message": f"Video with id {pk} is {video.status} and has nothing "
                    "to resume yet"
                },
                status=status.HTTP_409_CONFLICT,
            )

        video.refresh_from_db()
        resume_video_task.delay(video_id=video.id)
        logger.info(f"Video with id {pk} was queued to resume")

        return Response(
            {
                "message": "The generation has been queued to carry on",
                "video": VideoSerializer(video).data,
            },
            status=status.HTTP_202_ACCEPTED,
        )

    @swagger_auto_schema(
        operation_description="Queues the render of the video. Returns 202; poll GET /video/{id}/ "
        "until its status becomes COMPLETED or FAILED, then read `output`.",
        method="PATCH",
    )
    @action(detail=True, methods=["PATCH"], throttle_classes=[RenderRateThrottle])
    def render_video(self, _, pk):
        vid = self.get_object()

        claimed = Video.objects.filter(
            pk=vid.pk, status__in=["READY", "COMPLETED"]
        ).update(status="RENDERING")

        if not claimed:
            vid.refresh_from_db()
            return Response(
                {
                    "message": f"Video with id {pk} is {vid.status} and cannot be rendered yet"
                },
                status=status.HTTP_409_CONFLICT,
            )

        vid.refresh_from_db()

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
