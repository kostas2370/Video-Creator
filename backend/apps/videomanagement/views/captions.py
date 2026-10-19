from pathlib import Path

from django.db import transaction
from django.http import FileResponse, HttpResponse
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import CaptionProject
from ..paginator import StandardResultsSetPagination
from ..serializers.captions import CaptionUploadSerializer, CaptionEditSerializer, CaptionProjectSerializer, CaptionProjectSummarySerializer, CaptionStyleSerializer
from ..services.captions import BUSY_STATUSES, CaptionConflict, project_cues, queue_caption_job
from ..services.subtitles import cues_to_srt
from ..throttling import CaptionRateThrottle


class CaptionProjectView(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CaptionProjectSerializer
    pagination_class = StandardResultsSetPagination
    queryset = CaptionProject.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset().filter(created_by=self.request.user)
        return queryset.defer("words", "style") if self.action == "list" else queryset

    def get_serializer_class(self):
        return CaptionProjectSummarySerializer if self.action == "list" else CaptionProjectSerializer

    def get_throttles(self):
        return [CaptionRateThrottle()] if self.action in {"create", "transcribe", "render"} else super().get_throttles()

    def create(self, request):
        serializer = CaptionUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        metadata = serializer.metadata
        style = CaptionStyleSerializer(data={})
        style.is_valid(raise_exception=True)
        project = CaptionProject.objects.create(
            created_by=request.user, source=serializer.validated_data["source"],
            title=serializer.validated_data.get("title") or Path(serializer.validated_data["source"].name).stem[:100],
            duration=metadata["duration"], width=metadata["width"], height=metadata["height"], style=style.validated_data,
        )
        try:
            queue_caption_job(project)
        except APIException as exc:
            # Retain the upload and its ID so the user can retry without reuploading.
            project.refresh_from_db()
            if exc.status_code != 503 or project.status != "FAILED":
                raise
        return Response(self.get_serializer(project).data, status=201)

    def partial_update(self, request, pk=None):
        project = self.get_object()
        with transaction.atomic():
            project = CaptionProject.objects.select_for_update().get(pk=project.pk)
            if project.status in BUSY_STATUSES:
                raise CaptionConflict()
            serializer = CaptionEditSerializer(project, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            if "revision" not in serializer.validated_data:
                raise ValidationError({"revision": "Reload this project before saving."})
            if serializer.validated_data.pop("revision") != project.updated_at:
                raise CaptionConflict("This project changed in another editor. Reload it before saving; your changes are still here.")
            for key, value in serializer.validated_data.items():
                setattr(project, key, {**project.style, **value} if key == "style" else value)
            if {"words", "style"} & serializer.validated_data.keys():
                old_output = project.output.name
                project.output = ""
                project.status = "READY" if project.words else "FAILED"
                if old_output:
                    transaction.on_commit(lambda: project.output.storage.delete(old_output))
            project.error = ""
            project.save()
        return Response(self.get_serializer(project).data)

    @action(detail=True, methods=["POST"])
    def transcribe(self, request, pk=None):
        project = self.get_object()
        if project.words:
            raise CaptionConflict("This project already has captions. Edit them in the word list.")
        queue_caption_job(project)
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
        response = HttpResponse(cues_to_srt(project_cues(project)), content_type="application/x-subrip; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="captions.srt"'
        return response

    @action(detail=True, methods=["GET"])
    def download(self, request, pk=None):
        project = self.get_object()
        if not project.output:
            raise ValidationError("Export the captioned video first.")
        return FileResponse(project.output.open("rb"), as_attachment=True, filename="captioned-video.mp4")
