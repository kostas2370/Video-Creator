from rest_framework.decorators import action

from apps.videomanagement.serializers.project_export import (
    ProjectExportOptionsSerializer,
)
from apps.videomanagement.services.videos.project_export import project_export_response


class ProjectExportMixin:
    @action(detail=True, methods=["GET"], url_path="export-project")
    def export_project(self, request, pk=None):
        video = self.get_object()
        options = ProjectExportOptionsSerializer(data=request.query_params)
        options.is_valid(raise_exception=True)
        return project_export_response(request, video, **options.validated_data)
