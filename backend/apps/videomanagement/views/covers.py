from django.http import FileResponse, HttpResponse
from django.utils.text import slugify
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from apps.videomanagement.services.media.covers import create_cover, save_cover

from ..serializers.covers import CoverSerializer
from ..utils.file_utils import stored_file_exists


class VideoCoverMixin:
    @action(detail=True, methods=["POST"])
    def cover_preview(self, request, pk=None):
        video = self.get_object()
        serializer = CoverSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        response = HttpResponse(
            create_cover(video, serializer.validated_data), content_type="image/png"
        )
        response["Cache-Control"] = "no-store"
        return response

    @action(detail=True, methods=["POST"])
    def cover(self, request, pk=None):
        video = self.get_object()
        serializer = CoverSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        video = save_cover(video, serializer.validated_data)
        return Response(
            {"cover": video.cover.url, "cover_settings": video.cover_settings}
        )

    @action(detail=True, methods=["GET"])
    def cover_download(self, request, pk=None):
        video = self.get_object()
        if not stored_file_exists(video.cover):
            raise NotFound("Create and save a cover first.")
        return FileResponse(
            video.cover.open("rb"),
            as_attachment=True,
            filename=f"{slugify(video.title) or 'video'}-cover.png",
            content_type="image/png",
        )
