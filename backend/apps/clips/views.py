from copy import copy

from django.db.models import (
    BooleanField,
    Case,
    Prefetch,
    Value,
    When,
    prefetch_related_objects,
)
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.videomanagement.paginator import StandardResultsSetPagination
from apps.videomanagement.throttling import TagGenerationRateThrottle

from .choices import ClipStatus
from .highlights import suggest_clips
from .hashtags import draft_hashtags, save_hashtags
from .models import Clip, ClipProject
from .protected_media import media_response
from .serializers import (
    ClipEditSerializer,
    ClipSerializer,
    ExportClipsSerializer,
    ProjectProgressSerializer,
    ProjectSerializer,
    ProjectSummarySerializer,
    ProjectUploadSerializer,
    SaveHashtagsSerializer,
    TranscriptSearchSerializer,
)
from .services import (
    create_project,
    delete_clip,
    delete_project,
    queue_exports,
    queue_project,
    save_clip,
)
from .throttling import ClipProcessingThrottle


class ClipProjectView(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ClipProject.objects.none()
        rows = ClipProject.objects.filter(created_by=self.request.user).defer(
            "transcript_parts"
        )
        if self.action == "list":
            return rows.defer("words")
        if self.action == "retrieve":
            return rows.prefetch_related("clips")
        return rows

    def get_serializer_class(self):
        return ProjectSummarySerializer if self.action == "list" else ProjectSerializer

    def get_throttles(self):
        if self.action == "hashtags" and self.request.method == "POST":
            return [TagGenerationRateThrottle()]
        return (
            [ClipProcessingThrottle()]
            if self.action in {"create", "retry", "export", "search_transcript"}
            else super().get_throttles()
        )

    def create(self, request):
        serializer = ProjectUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = create_project(
            request.user,
            metadata=getattr(serializer, "metadata", None),
            **serializer.validated_data,
        )
        return Response(self.get_serializer(project).data, status=201)

    def destroy(self, request, pk=None):
        delete_project(self.get_object())
        return Response(status=204)

    @action(detail=True, methods=["post"])
    def retry(self, request, pk=None):
        return Response(
            self.get_serializer(queue_project(self.get_object())).data, status=202
        )

    @action(detail=True, methods=["post"])
    def clips(self, request, pk=None):
        project = self.get_object()
        serializer = ClipEditSerializer(data=request.data, context={"project": project})
        serializer.is_valid(raise_exception=True)
        clip = save_clip(project, dict(serializer.validated_data))
        return Response(
            ClipSerializer(clip, context=self.get_serializer_context()).data, status=201
        )

    @action(
        detail=True,
        methods=["get", "patch", "delete"],
        url_path=r"clips/(?P<clip_id>[^/.]+)",
    )
    def clip(self, request, pk=None, clip_id=None):
        project = self.get_object()
        if request.method == "DELETE":
            delete_clip(project, clip_id)
            return Response(status=204)
        clip = get_object_or_404(project.clips, pk=clip_id)
        if request.method == "GET":
            return Response(
                ClipSerializer(clip, context=self.get_serializer_context()).data
            )
        serializer = ClipEditSerializer(
            clip, data=request.data, partial=True, context={"project": project}
        )
        serializer.is_valid(raise_exception=True)
        clip = save_clip(project, dict(serializer.validated_data), clip.pk)
        return Response(
            ClipSerializer(clip, context=self.get_serializer_context()).data
        )

    @action(detail=True, methods=["post"])
    def export(self, request, pk=None):
        serializer = ExportClipsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        clips = queue_exports(self.get_object(), serializer.validated_data["clip_ids"])
        return Response(
            ClipSerializer(
                clips, many=True, context=self.get_serializer_context()
            ).data,
            status=202,
        )

    @action(
        detail=True, methods=["get"], url_path=r"clips/(?P<clip_id>[^/.]+)/download"
    )
    def download(self, request, pk=None, clip_id=None):
        clip = get_object_or_404(self.get_object().clips, pk=clip_id)
        if clip.status != ClipStatus.COMPLETED or not clip.output:
            raise ValidationError("Export this clip before downloading it.")
        return media_response(request, clip.output, filename=f"clip-{clip.pk}.mp4")

    @action(
        detail=True,
        methods=["post", "patch"],
        url_path=r"clips/(?P<clip_id>[^/.]+)/hashtags",
    )
    def hashtags(self, request, pk=None, clip_id=None):
        clip = get_object_or_404(self.get_object().clips, pk=clip_id)
        if request.method == "POST":
            return Response({"hashtags": draft_hashtags(clip, request.user)})
        serializer = SaveHashtagsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        clip = save_hashtags(clip, **serializer.validated_data)
        return Response({"hashtags": clip.hashtags})

    @action(detail=True, methods=["get"])
    def progress(self, request, pk=None):
        project = get_object_or_404(
            self.get_queryset()
            .annotate(
                has_transcript=Case(
                    When(words=[], then=Value(False)),
                    default=Value(True),
                    output_field=BooleanField(),
                )
            )
            .defer("words"),
            pk=pk,
        )
        prefetch_related_objects(
            [project],
            Prefetch(
                "clips",
                queryset=Clip.objects.only(
                    "id", "project_id", "status", "error", "updated_at", "hashtags"
                ),
            ),
        )
        return Response(
            ProjectProgressSerializer(
                project, context=self.get_serializer_context()
            ).data
        )

    @action(detail=True, methods=["post"], url_path="search-transcript")
    def search_transcript(self, request, pk=None):
        project = copy(self.get_object())
        serializer = TranscriptSearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not project.words:
            raise ValidationError("Wait for the transcript before searching for clips.")
        project.extraction_prompt = serializer.validated_data["prompt"]
        project.clip_count = 3
        return Response({"clips": suggest_clips(project)})

    @action(detail=True, methods=["get"])
    def source(self, request, pk=None):
        return media_response(request, self.get_object().source)

    @action(detail=True, methods=["get"])
    def preview(self, request, pk=None):
        return media_response(request, self.get_object().preview)

    @action(detail=True, methods=["get"], url_path=r"clips/(?P<clip_id>[^/.]+)/output")
    def output(self, request, pk=None, clip_id=None):
        clip = get_object_or_404(self.get_object().clips, pk=clip_id)
        return media_response(request, clip.output)
