from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from apps.videomanagement.paginator import AssetResultsPagination
from apps.videomanagement.models import Icon
from apps.videomanagement.serializers.icons import IconDetailSerializer, IconSerializer
from apps.videomanagement.services.media.icons import search_icons


class IconListView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = IconSerializer
    pagination_class = AssetResultsPagination

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Icon.objects.none()
        keys = self.request.query_params.get("keys")
        icons = search_icons(self.request.query_params.get("search", "")[:300],
                             keys=keys[:3000].split(",")[:24] if keys is not None else None,
                             user=self.request.user)
        return icons.filter(created_by=self.request.user) if self.request.query_params.get("mine") == "true" else icons


class IconDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = IconDetailSerializer
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Icon.objects.none()
        return Icon.objects.filter(created_by=self.request.user)

    def perform_destroy(self, instance):
        artwork = instance.file
        instance.delete()
        artwork.delete(save=False)
