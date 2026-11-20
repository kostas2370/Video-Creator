from urllib.parse import urlencode

from django.http import StreamingHttpResponse
from django.urls import reverse
from django.utils.http import content_disposition_header
from django.utils.text import slugify
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.videomanagement.serializers.project_export import (
    ProjectExportOptionsSerializer,
)
from apps.videomanagement.services.videos.project_export import (
    prepare_project_export,
    project_zip_chunks,
)


class ProjectExportMixin:
    @action(detail=True, methods=["GET"], url_path="export-project")
    def export_project(self, request, pk=None):
        video = self.get_object()
        options = ProjectExportOptionsSerializer(data=request.query_params)
        options.is_valid(raise_exception=True)
        include_output = options.validated_data["include_output"]
        manifest, archive = prepare_project_export(video, include_output=include_output)
        filename = (
            f"{slugify(video.title, allow_unicode=True)[:80] or 'video'}-project.zip"
        )
        if options.validated_data["check_only"]:
            url = reverse("video-export-project", args=[video.pk])
            return Response(
                {
                    "download_url": request.build_absolute_uri(url)
                    + "?"
                    + urlencode({"include_output": str(include_output).lower()}),
                    "filename": filename,
                    "media_count": len(archive.files),
                    "media_bytes": sum(
                        entry["size"] for _, entry in archive.files.values()
                    ),
                },
                headers={"Cache-Control": "no-store"},
            )
        response = StreamingHttpResponse(
            project_zip_chunks(manifest, archive), content_type="application/zip"
        )
        response["Content-Disposition"] = content_disposition_header(True, filename)
        response["Cache-Control"] = "private, no-store"
        response["Referrer-Policy"] = "no-referrer"
        response["X-Content-Type-Options"] = "nosniff"
        response["X-Accel-Buffering"] = "no"
        return response
