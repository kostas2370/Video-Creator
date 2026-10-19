from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.decorators import action
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
