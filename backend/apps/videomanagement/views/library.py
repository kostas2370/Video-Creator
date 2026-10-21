from pathlib import Path

from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.videomanagement.filters import MediaAssetFilter
from apps.videomanagement.services.media.library import (
    delete_media_asset,
    use_media_asset,
)

from ..models import MediaAsset, Video
from ..paginator import AssetResultsPagination
from ..permissions import IsOwnerPermission
from ..serializers.library import MediaAssetSerializer, UseMediaSerializer
from ..utils.file_utils import stored_file_exists


class MediaAssetView(viewsets.ModelViewSet):
    filter_backends = [DjangoFilterBackend]
    filterset_class = MediaAssetFilter
    queryset = MediaAsset.objects.all()
    serializer_class = MediaAssetSerializer
    permission_classes = [IsAuthenticated, IsOwnerPermission]
    pagination_class = AssetResultsPagination
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return MediaAsset.objects.none()
        return MediaAsset.objects.filter(created_by=self.request.user)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_destroy(self, instance):
        delete_media_asset(instance)

    @action(detail=True, methods=["GET"])
    def download(self, request, pk=None):
        asset = self.get_object()
        if not stored_file_exists(asset.file):
            raise NotFound("This library file is missing.")
        return FileResponse(
            asset.file.open("rb"),
            as_attachment=True,
            filename=f"{asset.title}{Path(asset.file.name).suffix}",
        )

    @action(detail=True, methods=["POST"])
    def use(self, request, pk=None):
        asset = self.get_object()
        serializer = UseMediaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = dict(serializer.validated_data)
        video = get_object_or_404(
            Video.objects.for_user(request.user), pk=values.pop("video_id")
        )
        scene = use_media_asset(asset, video, **values)
        return Response(
            {"video_id": str(video.pk), "scene_id": str(scene.pk) if scene else None}
        )
