from django.http import FileResponse, HttpResponse
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.videomanagement.services.captions.projects import (
    create_caption_project,
    project_cues,
    queue_caption_job,
    update_caption_project,
)
from apps.videomanagement.utils.captions.cues import cues_to_srt

from ..models import CaptionProject
from ..paginator import StandardResultsSetPagination
from ..serializers.captions import (
    CaptionEditSerializer,
    CaptionProjectSerializer,
    CaptionProjectSummarySerializer,
    CaptionUploadSerializer,
)
from ..throttling import CaptionRateThrottle


class CaptionProjectView(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    permission_classes = [IsAuthenticated]
    serializer_class = CaptionProjectSerializer
    pagination_class = StandardResultsSetPagination
    queryset = CaptionProject.objects.all()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return CaptionProject.objects.none()
        queryset = super().get_queryset().filter(created_by=self.request.user)
        return queryset.defer("words", "style") if self.action == "list" else queryset

    def get_serializer_class(self):
        return (
            CaptionProjectSummarySerializer
            if self.action == "list"
            else CaptionProjectSerializer
        )

    def get_throttles(self):
        return (
            [CaptionRateThrottle()]
            if self.action in {"create", "transcribe", "render"}
            else super().get_throttles()
        )

    def create(self, request):
        serializer = CaptionUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = create_caption_project(
            request.user, metadata=serializer.metadata, **serializer.validated_data
        )
        return Response(self.get_serializer(project).data, status=201)

    def partial_update(self, request, pk=None):
        project = self.get_object()
        serializer = CaptionEditSerializer(project, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        project = update_caption_project(project, **serializer.validated_data)
        return Response(self.get_serializer(project).data)

    @action(detail=True, methods=["POST"])
    def transcribe(self, request, pk=None):
        project = queue_caption_job(self.get_object())
        return Response(self.get_serializer(project).data, status=202)

    @action(detail=True, methods=["POST"])
    def render(self, request, pk=None):
        project = queue_caption_job(self.get_object(), render=True)
        return Response(self.get_serializer(project).data, status=202)

    @action(detail=True, methods=["GET"])
    def subtitles(self, request, pk=None):
        project = self.get_object()
        if not project.words:
            raise ValidationError("Generate or add caption words first.")
        response = HttpResponse(
            cues_to_srt(project_cues(project)),
            content_type="application/x-subrip; charset=utf-8",
        )
        response["Content-Disposition"] = 'attachment; filename="captions.srt"'
        return response

    @action(detail=True, methods=["GET"])
    def download(self, request, pk=None):
        project = self.get_object()
        if not project.output:
            raise ValidationError("Export the captioned video first.")
        return FileResponse(
            project.output.open("rb"),
            as_attachment=True,
            filename="captioned-video.mp4",
        )
