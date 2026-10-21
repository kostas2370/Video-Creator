import logging

from django.db.models import OuterRef, Subquery
from django.http import HttpResponse
from django.utils.http import content_disposition_header
from django.utils.text import slugify
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.videomanagement.filters import VideoFilter
from apps.videomanagement.models import SceneImage, Video, VideoStatus, VideoType
from apps.videomanagement.paginator import StandardResultsSetPagination
from apps.videomanagement.permissions import IsOwnerPermission
from apps.videomanagement.schemas.drafts import StoryDraftResultSerializer
from apps.videomanagement.serializers.audio import (
    MusicAudioSerializer,
    VoiceoverUploadSerializer,
)
from apps.videomanagement.serializers.models import (
    VideoNestedSerializer,
    VideoSerializer,
)
from apps.videomanagement.serializers.preview import PreviewTimelineSerializer
from apps.videomanagement.serializers.requests import (
    AddSceneSerializer,
    AddScenesSerializer,
    BulkAutoMotionSerializer,
    ManualSceneSerializer,
    ManualVideoSerializer,
    ReorderScenesSerializer,
    SceneDraftSerializer,
    StoryboardSerializer,
    StoryDraftSerializer,
    StoryVideoSerializer,
    VideoNotesSerializer,
    VideoUpdateSerializer,
)
from apps.videomanagement.services.captions.subtitles import export_subtitles
from apps.videomanagement.services.media.music import set_music
from apps.videomanagement.services.scenes.editing import (
    apply_auto_motion,
    reorder_scenes,
)
from apps.videomanagement.services.scenes.generation import draft_scene
from apps.videomanagement.services.videos.jobs import (
    approve_script,
    queue_render,
    queue_resume,
    queue_scene_creation,
)
from apps.videomanagement.services.videos.manual import (
    add_manual_scene,
    create_manual_video,
)
from apps.videomanagement.services.videos.notes import update_notes
from apps.videomanagement.services.videos.settings import (
    delete_video,
    update_music_settings,
    video_update,
)
from apps.videomanagement.services.videos.story import create_story_project, draft_story
from apps.videomanagement.throttling import (
    RenderRateThrottle,
    ResumeRateThrottle,
    StoryDraftRateThrottle,
)
from apps.videomanagement.utils.captions.styles import style_catalog
from apps.videomanagement.views.covers import VideoCoverMixin
from apps.videomanagement.views.tags import VideoTagsMixin
from apps.videomanagement.views.thumbnails import VideoThumbnailMixin

logger = logging.getLogger(__name__)


class VideoView(
    VideoThumbnailMixin,
    VideoTagsMixin,
    VideoCoverMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = VideoSerializer
    queryset = Video.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ["title", "tags__tiktok", "tags__youtube", "tags__search"]
    filterset_class = VideoFilter
    permission_classes = [IsAuthenticated, IsOwnerPermission]
    pagination_class = StandardResultsSetPagination

    @action(detail=True, methods=["PATCH"])
    def favorite(self, request, pk=None):
        video = self.get_object()
        video.toggle_favorite()
        return Response({"is_favorite": video.is_favorite})

    @action(detail=False, methods=["GET"])
    def caption_styles(self, request):
        return Response(style_catalog())

    @swagger_auto_schema(request_body=ManualVideoSerializer)
    @action(detail=False, methods=["POST"])
    def manual(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        video = create_manual_video(request.user, **serializer.validated_data)
        return Response(VideoNestedSerializer(video).data, status=201)

    @swagger_auto_schema(
        request_body=StoryDraftSerializer, responses={200: StoryDraftResultSerializer}
    )
    @action(detail=False, methods=["POST"], throttle_classes=[StoryDraftRateThrottle])
    def draft_story(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(draft_story(request.user, **serializer.validated_data))

    @swagger_auto_schema(request_body=StoryVideoSerializer)
    @action(detail=False, methods=["POST"])
    def story(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        video, warning = create_story_project(request.user, **serializer.validated_data)
        data = dict(VideoNestedSerializer(video).data)
        if warning:
            data["warning"] = warning
        return Response(data, status=201 if warning else 202)

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
        if getattr(self, "swagger_fake_view", False):
            return Video.objects.none()
        queryset = (
            Video.objects.for_user(self.request.user)
            .order_by("-updated_at", "-id")
            .select_related("music", "prompt")
        )
        if self.action == "list":
            queryset = queryset.listable().annotate(
                scene_preview=Subquery(
                    SceneImage.objects.filter(scene__video_id=OuterRef("pk"))
                    .exclude(asset__file="")
                    .exclude(asset__file__isnull=True)
                    .order_by("scene__position", "created_at", "id")
                    .values("asset__file")[:1]
                )
            )

        if self.action in ("retrieve", "preview"):
            queryset = queryset.select_related("intro", "outro").prefetch_related(
                "scenes__scene_images__asset"
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
            "notes": VideoNotesSerializer,
            "story": StoryVideoSerializer,
            "draft_story": StoryDraftSerializer,
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

    def get_throttles(self):
        if self.action in ("approve_script", "resume", "story"):
            return [ResumeRateThrottle()]
        if self.action == "render_video":
            return [RenderRateThrottle()]
        return super().get_throttles()

    def get_parsers(self):
        # DRF sets self.action after parsers; resolve the route from the raw request.
        action = getattr(self, "action", None) or getattr(self, "action_map", {}).get(
            self.request.method.lower()
        )
        if action in ("music", "story"):
            return [MultiPartParser(), FormParser()]
        return super().get_parsers()

    def serialize_video_detail(self, video):
        # Reload after editing: services may return a locked instance, and
        # relations fetched before an edit may no longer describe its output.
        video = (
            self.get_queryset()
            .select_related("intro", "outro")
            .prefetch_related("scenes__scene_images__asset")
            .get(pk=video.pk)
        )
        return VideoNestedSerializer(video).data

    def perform_destroy(self, instance):
        delete_video(instance)

    @swagger_auto_schema(request_body=MusicAudioSerializer)
    @action(detail=True, methods=["PATCH"])
    def audio(self, request, pk=None):
        video = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        video = update_music_settings(video, serializer.validated_data)
        return Response(self.serialize_video_detail(video))

    @action(detail=True, methods=["GET"])
    def subtitles(self, request, pk=None):
        video = self.get_object()
        response = HttpResponse(
            export_subtitles(video), content_type="application/x-subrip; charset=utf-8"
        )
        filename = (
            f"{slugify(video.title, allow_unicode=True)[:80] or 'video'}-subtitles.srt"
        )
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
        outcome = video_update(video, **serializer.validated_data)
        logger.info(f"Video with id {pk}  got updated successfully")
        return Response(
            {
                "message": "Updated Success",
                "video": self.serialize_video_detail(outcome),
            }
        )

    @action(detail=True, methods=["PATCH"])
    def notes(self, request, pk=None):
        video = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        video = update_notes(video, **serializer.validated_data)
        return Response({"notes": video.notes})

    @action(detail=True, methods=["POST"])
    def approve_script(self, request, pk=None):
        video = self.get_object()
        serializer = self.get_serializer(
            data=request.data,
            context={
                **self.get_serializer_context(),
                "narration": (video.settings or {}).get("narration", True),
            },
        )
        serializer.is_valid(raise_exception=True)
        video = approve_script(video, serializer.validated_data)
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
        video = queue_resume(self.get_object())
        return Response(
            {
                "message": "The generation has been queued to carry on",
                "video": VideoSerializer(video).data,
            },
            status=202,
        )

    @swagger_auto_schema(
        operation_description="Queues the render of the video. Returns 202; poll GET /video/{id}/ "
        "until its status becomes COMPLETED or FAILED, then read `output`.",
        method="PATCH",
    )
    @action(detail=True, methods=["PATCH"])
    def render_video(self, _, pk):
        video = queue_render(self.get_object())
        return Response(
            {
                "message": "The render has been queued",
                "video": VideoSerializer(video).data,
            },
            status=202,
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
        serializer = self.get_serializer(
            data=request.data, context={**self.get_serializer_context(), "video": video}
        )
        serializer.is_valid(raise_exception=True)
        if video.video_type == VideoType.MANUAL:
            add_manual_scene(video, **serializer.validated_data)
            return Response(self.serialize_video_detail(video), status=201)
        queue_scene_creation(
            video, serializer.validated_data, request.FILES.get("image")
        )
        return Response(
            {"message": "Scene creation queued", "status": VideoStatus.GENERATION},
            status=202,
        )

    @swagger_auto_schema(request_body=BulkAutoMotionSerializer)
    @action(detail=True, methods=["PATCH"])
    def auto_motion(self, request, pk=None):
        owned_video = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        video = apply_auto_motion(
            owned_video, serializer.validated_data["motion_intensity"]
        )
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
