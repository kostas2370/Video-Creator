import logging

from django.core.files.storage import default_storage
from pathlib import Path
from uuid import uuid4
from django.utils import timezone
from django.db import transaction

from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import OrderingFilter, SearchFilter

from rest_framework.permissions import IsAuthenticated

from ..events import publish_update
from ..models import Video, VideoStatus
from ..paginator import StandardResultsSetPagination
from ..request_serializers import VideoUpdateSerializer, AddSceneSerializer, AddScenesSerializer, SceneDraftSerializer, StoryboardSerializer
from ..serializers import VideoSerializer, VideoNestedSerializer
from ..services.SceneServices import draft_scene
from ..tasks import render_video_task, resume_video_task, create_scene_task, generate_video_task
from ..throttling import RenderRateThrottle, ResumeRateThrottle
from ..permissions import AiGenerationLimitPermission, IsOwnerPermission, SceneGenerationLimitPermission

from ..utils.cost_utils import reserve_scene_credit

logger = logging.getLogger(__name__)


class VideoView(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
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
            .order_by("-created_at")
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
        video = self.get_object()
        serializer = self.get_serializer(video, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        outcome = serializer.save()
        logger.info(f"Video with id {pk}  got updated successfully")
        return Response(
            {"message": "Updated Success", "video": VideoNestedSerializer(outcome).data}
        )

    @action(detail=True, methods=["POST"], throttle_classes=[ResumeRateThrottle],
            permission_classes=[IsAuthenticated, IsOwnerPermission, AiGenerationLimitPermission])
    def approve_script(self, request, pk=None):
        owned_video = self.get_object()
        with transaction.atomic():
            video = Video.objects.select_for_update().get(pk=owned_video.pk)
            if video.status != VideoStatus.REVIEW:
                return Response({"detail": "This video is not awaiting review."}, status=409)
            serializer = StoryboardSerializer(
                data=request.data, context={"narration": video.settings.get("narration", True)}
            )
            serializer.is_valid(raise_exception=True)
            params = video.settings.get("generation_params")
            if not params:
                return Response({"detail": "Generation settings are missing."}, status=409)
            video.gpt_answer = dict(serializer.validated_data)
            video.title = video.gpt_answer["title"]
            video.status = VideoStatus.GENERATION
            video.save()
        try:
            generate_video_task.delay(video_id=video.id, **params)
        except Exception:
            video.status = VideoStatus.REVIEW
            video.save(update_fields=["status"])
            return Response({"detail": "Could not queue generation. Your draft is saved. Try again."}, status=503)
        publish_update(f"video.{video.pk}", video_id=video.pk)
        return Response({"video": VideoSerializer(video).data}, status=202)

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
            pk=video.pk, status__in=[VideoStatus.FAILED, VideoStatus.READY]
        ).update(status=VideoStatus.GENERATION)

        if not claimed:
            video.refresh_from_db()
            return Response(
                {
                    "message": f"Video with id {pk} is {video.status} and has nothing "
                    "to resume yet"
                },
                status=status.HTTP_409_CONFLICT,
            )

        publish_update(f"video.{video.pk}", video_id=video.pk)
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
            pk=vid.pk, status__in=[VideoStatus.READY, VideoStatus.COMPLETED]
        ).update(status=VideoStatus.RENDERING)

        if not claimed:
            vid.refresh_from_db()
            return Response(
                {
                    "message": f"Video with id {pk} is {vid.status} and cannot be rendered yet"
                },
                status=status.HTTP_409_CONFLICT,
            )

        publish_update(f"video.{vid.pk}", video_id=vid.pk)
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
        operation_description="Queues a single scene or a JSON scenes array of up to 12 scenes. "
        "Returns 202; poll the video status for completion.",
        method="POST",
        request_body=AddSceneSerializer,
    )
    @action(detail=True, methods=["POST"])
    def add_scene(self, request, pk):
        video = self.get_object()
        is_batch = "scenes" in request.data
        if is_batch and request.FILES:
            return Response({"detail": "Upload a visual when adding a single scene."}, status=400)
        serializer_class = AddScenesSerializer if is_batch else AddSceneSerializer
        serializer = serializer_class(data=request.data, context={"video": video})
        serializer.is_valid(raise_exception=True)
        claimed = Video.objects.filter(
            pk=video.pk, status__in=[VideoStatus.READY, VideoStatus.COMPLETED, VideoStatus.FAILED]
        ).update(status=VideoStatus.GENERATION, updated_at=timezone.now())
        if not claimed:
            return Response({"detail": "Wait for the current video operation to finish."}, status=409)
        publish_update(f"video.{video.pk}", video_id=video.pk)
        upload_path = None
        try:
            upload = request.FILES.get("image")
            if upload:
                upload_path = default_storage.save(
                    f"media/scene_uploads/{uuid4().hex}/{Path(upload.name).name}", upload
                )
            create_scene_task.delay(video.pk, dict(serializer.validated_data), upload_path)
        except Exception:
            logger.exception("Could not queue scene for video %s", video.pk)
            Video.objects.filter(pk=video.pk, status=VideoStatus.GENERATION).update(status=video.status)
            publish_update(f"video.{video.pk}", video_id=video.pk)
            if upload_path:
                default_storage.delete(upload_path)
            return Response({"detail": "Could not queue the scene. Please try again."}, status=503)
        return Response(
            {"message": "Scene creation queued", "status": VideoStatus.GENERATION},
            status=status.HTTP_202_ACCEPTED,
        )

    @swagger_auto_schema(request_body=SceneDraftSerializer)
    @action(detail=True, methods=["POST"], permission_classes=[
        IsAuthenticated, IsOwnerPermission, SceneGenerationLimitPermission,
    ])
    def draft_scene(self, request, pk):
        video = self.get_object()
        serializer = SceneDraftSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with reserve_scene_credit(request.user, 0.03, SceneGenerationLimitPermission.required_limit):
            draft = draft_scene(video, **serializer.validated_data)
        return Response(draft)
