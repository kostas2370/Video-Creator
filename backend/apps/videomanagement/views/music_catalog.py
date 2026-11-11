from pathlib import Path

from django.db.models import Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.videomanagement.filters import MusicCatalogFilter
from apps.videomanagement.models import MusicCatalogTrack, Video
from apps.videomanagement.paginator import AssetResultsPagination
from apps.videomanagement.serializers.library import (
    MusicCatalogTrackSerializer,
    UseMediaSerializer,
)
from apps.videomanagement.services.media.catalog import (
    select_music_track,
    set_catalog_music,
)
from apps.videomanagement.services.scenes.editing import editable_video
from apps.videomanagement.utils.file_utils import stored_file_exists


class MusicCatalogView(viewsets.ReadOnlyModelViewSet):
    queryset = MusicCatalogTrack.objects.filter(approved=True).exclude(
        Q(file="") | Q(license_url="")
    )
    serializer_class = MusicCatalogTrackSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = AssetResultsPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = MusicCatalogFilter

    @action(detail=True, methods=["GET"])
    def download(self, request, pk=None):
        track = self.get_object()
        if not stored_file_exists(track.file):
            raise NotFound("This catalog file is missing.")
        return FileResponse(
            track.file.open("rb"),
            as_attachment=True,
            filename=f"{track.title}{Path(track.file.name).suffix}",
        )

    @action(detail=True, methods=["POST"])
    def use(self, request, pk=None):
        track = self.get_object()
        choices = UseMediaSerializer(data=request.data)
        choices.is_valid(raise_exception=True)
        if choices.validated_data["purpose"] != "music":
            raise ValidationError(
                "Catalog tracks can only be used as background music."
            )
        video = get_object_or_404(
            Video.objects.for_user(request.user), pk=choices.validated_data["video_id"]
        )
        if not stored_file_exists(track.file):
            raise NotFound("This catalog file is missing.")
        set_catalog_music(video, track)
        return Response({"video_id": str(video.pk), "scene_id": None})

    @action(detail=False, methods=["POST"], url_path="auto-select")
    def auto_select(self, request):
        choices = UseMediaSerializer(
            data={"video_id": request.data.get("video_id"), "purpose": "music"}
        )
        choices.is_valid(raise_exception=True)
        video = get_object_or_404(
            Video.objects.for_user(request.user), pk=choices.validated_data["video_id"]
        )
        with editable_video(video.pk) as locked:
            track = select_music_track(locked)
            set_catalog_music(locked, track)
        return Response(
            {"video_id": str(video.pk), "track": self.get_serializer(track).data}
        )
