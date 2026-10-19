import logging

from django.core.files.storage import default_storage
from pathlib import Path
from uuid import uuid4
from django.utils import timezone
from django.http import HttpResponse
from django.utils.http import content_disposition_header
from django.utils.text import slugify
from django.db import transaction
from rest_framework.parsers import MultiPartParser, FormParser

from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import OrderingFilter, SearchFilter

from rest_framework.permissions import IsAuthenticated

from ..services.caption_styles import style_catalog
from ..events import publish_update
from ..models import Video, VideoStatus, VideoType
from ..serializers.requests import ManualVideoSerializer, ManualSceneSerializer
from ..serializers.audio import VoiceoverUploadSerializer
from ..services.manual import create_manual_video, add_manual_scene, set_music
from ..paginator import StandardResultsSetPagination
from ..serializers.requests import BulkAutoMotionSerializer, VideoUpdateSerializer, AddSceneSerializer, AddScenesSerializer, SceneDraftSerializer, StoryboardSerializer, ReorderScenesSerializer
from ..serializers.models import VideoSerializer, VideoNestedSerializer
from ..serializers.preview import PreviewTimelineSerializer
from ..services.SceneServices import draft_scene
from ..services.editing import reorder_scenes, apply_auto_motion
from ..services.editing import editable_video, changed
from ..services.subtitles import export_subtitles
from ..tasks import render_video_task, resume_video_task, create_scene_task, generate_video_task
from ..throttling import RenderRateThrottle, ResumeRateThrottle
from ..permissions import IsOwnerPermission

from ..serializers.audio import MusicAudioSerializer

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

    @swagger_auto_schema(request_body=ManualVideoSerializer)
    @action(detail=False, methods=["GET"])
    def caption_styles(self, request):
        return Response(style_catalog())

    @action(detail=False, methods=["POST"])
    def manual(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        video = create_manual_video(request.user, **serializer.validated_data)
        return Response(VideoNestedSerializer(video).data, status=201)

    @action(detail=True, methods=["POST", "DELETE"])
    def music(self, request, pk=None):
        video = self.get_object()
        upload = None
        if request.method == "POST":
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            upload = serializer.validated_data["file"]
        video = set_music(video, upload)
        return Response(self.serialize_video_detail(video))

    def get_queryset(self):
        queryset = (
            Video.objects.for_user(self.request.user)
            .order_by("-created_at")
            .select_related("music", "prompt")
        )
        if self.action == "list":
            queryset = queryset.listable()

        if self.action in ("retrieve", "preview"):
            queryset = queryset.select_related("intro", "outro").prefetch_related(
                "scenes__scene_images"
            )

        return queryset

    def get_serializer_class(self):
        if self.action == "add_scene" and not getattr(self, "swagger_fake_view", False):
            if self.get_object().video_type == VideoType.MANUAL:
                return ManualSceneSerializer
            if "scenes" in self.request.data:
                return AddScenesSerializer
        serializer_class = {
            "manual": ManualVideoSerializer,
            "music": VoiceoverUploadSerializer,
            "audio": MusicAudioSerializer,
            "approve_script": StoryboardSerializer,
            "auto_motion": BulkAutoMotionSerializer,
            "reorder_scenes": ReorderScenesSerializer,
            "draft_scene": SceneDraftSerializer,
            "retrieve": VideoNestedSerializer,
            "partial_update": VideoUpdateSerializer,
            "add_scene": AddSceneSerializer,
            "preview": PreviewTimelineSerializer,
        }

        return serializer_class.get(self.action, VideoSerializer)

    def get_permissions(self):
        return super().get_permissions()

    def get_throttles(self):
        if self.action in ("approve_script", "resume"):
            return [ResumeRateThrottle()]
        if self.action == "render_video":
            return [RenderRateThrottle()]
        return super().get_throttles()

    def get_parsers(self):
        # DRF sets self.action after parsers; resolve the route from the raw request.
        action = getattr(self, "action", None) or getattr(self, "action_map", {}).get(
            self.request.method.lower()
        )
        if action == "music":
            return [MultiPartParser(), FormParser()]
        return super().get_parsers()

    def serialize_video_detail(self, video):
        # Reload after editing: services may return a locked instance, and
        # relations fetched before an edit may no longer describe its output.
        video = (
            self.get_queryset()
            .select_related("intro", "outro")
            .prefetch_related("scenes__scene_images")
            .get(pk=video.pk)
        )
        return VideoNestedSerializer(video).data

    def perform_destroy(self, instance):
        with editable_video(instance.pk) as video:
            video.delete()

    @swagger_auto_schema(request_body=MusicAudioSerializer)
    @action(detail=True, methods=["PATCH"])
    def audio(self, request, pk=None):
        owned = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with editable_video(owned.pk) as video:
            video.settings = {**(video.settings or {}), **serializer.validated_data}
            video.save(update_fields=["settings"])
            changed(video)
        return Response(self.serialize_video_detail(video))

    @action(detail=True, methods=["GET"])
    def subtitles(self, request, pk=None):
        video = self.get_object()
        response = HttpResponse(export_subtitles(video), content_type="application/x-subrip; charset=utf-8")
        filename = f"{slugify(video.title, allow_unicode=True)[:80] or 'video'}-subtitles.srt"
        response["Content-Disposition"] = content_disposition_header(True, filename)
        response["Cache-Control"] = "private, no-store"
        return response

    @swagger_auto_schema(responses={200: PreviewTimelineSerializer})
    @action(detail=True, methods=["GET"])
    def preview(self, request, pk=None):
        response = Response(self.get_serializer(self.get_object()).data)
        response["Cache-Control"] = "private, no-store"
        return response

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
            {"message": "Updated Success", "video": self.serialize_video_detail(outcome)}
        )

    @action(detail=True, methods=["POST"])
    def approve_script(self, request, pk=None):
        owned_video = self.get_object()
        with transaction.atomic():
            video = Video.objects.select_for_update().get(pk=owned_video.pk)
            if video.status != VideoStatus.REVIEW:
                return Response({"detail": "This video is not awaiting review."}, status=409)
            serializer = self.get_serializer(
                data=request.data, context={**self.get_serializer_context(), "narration": video.settings.get("narration", True)}
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
        "worked on again. Returns 202; "
        "poll GET /video/{id}/ until its status becomes READY or FAILED.",
        method="PATCH",
    )
    @action(detail=True, methods=["PATCH"])
    def resume(self, _, pk):
        video = self.get_object()

        if video.video_type == VideoType.MANUAL:
            return Response({"detail": "Manual projects do not need AI generation. Edit your scenes and render again."}, status=409)

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
    @action(detail=True, methods=["PATCH"])
    def render_video(self, _, pk):
        vid = self.get_object()
        if vid.video_type == VideoType.MANUAL and vid.status in (VideoStatus.READY, VideoStatus.COMPLETED) and not vid.scenes.exists():
            return Response({"detail": "Add a scene before rendering your video."}, status=400)

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
        if video.video_type == VideoType.MANUAL:
            serializer = self.get_serializer(data=request.data, context={**self.get_serializer_context(), "video": video})
            serializer.is_valid(raise_exception=True)
            add_manual_scene(video, **serializer.validated_data)
            return Response(self.serialize_video_detail(video), status=201)
        is_batch = "scenes" in request.data
        if is_batch and request.FILES:
            return Response({"detail": "Upload a visual when adding a single scene."}, status=400)
        serializer = self.get_serializer(data=request.data, context={**self.get_serializer_context(), "video": video})
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

    @swagger_auto_schema(request_body=BulkAutoMotionSerializer)
    @action(detail=True, methods=["PATCH"])
    def auto_motion(self, request, pk=None):
        owned_video = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        video = apply_auto_motion(owned_video, serializer.validated_data["motion_intensity"])
        return Response(self.serialize_video_detail(video))

    @swagger_auto_schema(request_body=ReorderScenesSerializer)
    @action(detail=True, methods=["POST"])
    def reorder_scenes(self, request, pk=None):
        owned_video = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        video = reorder_scenes(owned_video, serializer.validated_data["scene_ids"])
        return Response(self.serialize_video_detail(video))

    @swagger_auto_schema(request_body=SceneDraftSerializer)
    @action(detail=True, methods=["POST"])
    def draft_scene(self, request, pk):
        video = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        draft = draft_scene(video, **serializer.validated_data)
        return Response(draft)
