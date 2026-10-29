from django.db import transaction
from django.http import FileResponse
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.videomanagement.paginator import StandardResultsSetPagination
from apps.videomanagement.throttling import BaseThrottle, TagGenerationRateThrottle

from .hashtags import draft_hashtags, save_hashtags
from .models import ClipProject
from .serializers import (
    ClipEditSerializer,
    ExportClipsSerializer,
    SaveHashtagsSerializer,
    ClipSerializer,
    ProjectSerializer,
    ProjectSummarySerializer,
    ProjectUploadSerializer,
)
from .services import (
    CLIP_BUSY,
    PROJECT_BUSY,
    STALE_AFTER,
    ClipConflict,
    create_project,
    queue_exports,
    queue_project,
    save_clip,
)


class ClipProcessingThrottle(BaseThrottle):
    scope = "clip_processing"
    rate = "10/hour"


class ClipProjectView(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ClipProject.objects.none()
        rows = ClipProject.objects.filter(created_by=self.request.user)
        return (
            rows.defer("words", "transcript_parts")
            if self.action == "list"
            else rows.prefetch_related("clips")
        )

    def get_serializer_class(self):
        return ProjectSummarySerializer if self.action == "list" else ProjectSerializer

    def get_throttles(self):
        if self.action == "hashtags" and self.request.method == "POST":
            return [TagGenerationRateThrottle()]
        return (
            [ClipProcessingThrottle()]
            if self.action in {"create", "retry", "export"}
            else super().get_throttles()
        )

    def create(self, request):
        serializer = ProjectUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = create_project(
            request.user, metadata=serializer.metadata, **serializer.validated_data
        )
        return Response(self.get_serializer(project).data, status=201)

    def destroy(self, request, pk=None):
        from django.utils import timezone

        with transaction.atomic():
            project = ClipProject.objects.select_for_update().get(
                pk=self.get_object().pk
            )
            fresh = timezone.now() - STALE_AFTER
            if (
                project.status in PROJECT_BUSY and project.updated_at > fresh
            ) or project.clips.filter(
                status__in=CLIP_BUSY, updated_at__gt=fresh
            ).exists():
                raise ClipConflict(
                    "Wait for processing to finish before deleting this project."
                )
            project.delete()
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
        detail=True, methods=["patch", "delete"], url_path=r"clips/(?P<clip_id>[^/.]+)"
    )
    def clip(self, request, pk=None, clip_id=None):
        project = self.get_object()
        clip = get_object_or_404(project.clips, pk=clip_id)
        if request.method == "DELETE":
            from .services import project_editable

            with transaction.atomic():
                locked = ClipProject.objects.select_for_update().get(pk=project.pk)
                project_editable(locked)
                clip.refresh_from_db()
                if clip.status in CLIP_BUSY:
                    raise ClipConflict(
                        "Wait for this clip's export to finish before removing it."
                    )
                clip.delete()
            return Response(status=204)
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
        if clip.status != "COMPLETED" or not clip.output:
            raise ValidationError("Export this clip before downloading it.")
        return FileResponse(
            clip.output.open("rb"), as_attachment=True, filename=f"clip-{clip.pk}.mp4"
        )

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
