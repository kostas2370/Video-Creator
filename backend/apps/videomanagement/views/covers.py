from uuid import uuid4

from django.core.files.base import ContentFile
from django.db import transaction
from django.http import HttpResponse, FileResponse
from django.utils.text import slugify
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import NotFound

from ..models import Video
from ..serializers.library import CoverSerializer
from ..services.covers import create_cover
from ..utils.file_utils import stored_file_exists


class VideoCoverMixin:
    @action(detail=True, methods=["POST"])
    def cover_preview(self, request, pk=None):
        video = self.get_object()
        serializer = CoverSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        response = HttpResponse(create_cover(video, serializer.validated_data), content_type="image/png")
        response["Cache-Control"] = "no-store"
        return response

    @action(detail=True, methods=["POST"])
    def cover(self, request, pk=None):
        owned = self.get_object()
        serializer = CoverSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            video = Video.objects.select_for_update().get(pk=owned.pk)
            image = create_cover(video, serializer.validated_data)
            old = video.cover.name
            video.cover.save(f"{video.pk}-{uuid4().hex}.png", ContentFile(image), save=False)
            try:
                video.cover_settings = serializer.validated_data
                video.save(update_fields=["cover", "cover_settings"])
            except Exception:
                video.cover.storage.delete(video.cover.name)
                raise
            if old:
                transaction.on_commit(lambda: video.cover.storage.delete(old), robust=True)
        return Response({"cover": video.cover.url, "cover_settings": video.cover_settings})

    @action(detail=True, methods=["GET"])
    def cover_download(self, request, pk=None):
        video = self.get_object()
        if not stored_file_exists(video.cover):
            raise NotFound("Create and save a cover first.")
        return FileResponse(video.cover.open("rb"), as_attachment=True,
                            filename=f"{slugify(video.title) or 'video'}-cover.png", content_type="image/png")
