from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from apps.videomanagement.serializers.project_export import (
    ProjectExportOptionsSerializer,
)
from apps.videomanagement.serializers.project_import import (
    ProjectImportUploadSerializer,
)
from apps.videomanagement.services.videos.project_export import project_export_response
from apps.videomanagement.services.videos.project_import import import_project


class ProjectArchiveMixin:
    @action(detail=True, methods=["GET"], url_path="export-project")
    def export_project(self, request, pk=None):
        video = self.get_object()
        options = ProjectExportOptionsSerializer(data=request.query_params)
        options.is_valid(raise_exception=True)
        return project_export_response(request, video, **options.validated_data)

    @action(
        detail=False,
        methods=["POST"],
        url_path="import-project",
        parser_classes=[MultiPartParser],
        serializer_class=ProjectImportUploadSerializer,
    )
    def import_project(self, request):
        options = self.get_serializer(data=request.data)
        options.is_valid(raise_exception=True)
        video = import_project(request.user, options.validated_data["file"])
        return Response({"id": str(video.pk), "title": video.title}, status=201)
