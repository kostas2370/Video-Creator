from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from apps.videomanagement.paginator import AssetResultsPagination
from apps.videomanagement.models import Icon
from apps.videomanagement.serializers.icons import IconDetailSerializer, IconSerializer
from apps.videomanagement.services.media.icons import search_icons


class IconListView(generics.ListCreateAPIView):
    queryset = Icon.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = IconSerializer
    pagination_class = AssetResultsPagination

    def filter_queryset(self, queryset):
        keys = self.request.query_params.get("keys")
        icons = search_icons(
            self.request.query_params.get("search", "")[:300],
            keys=keys[:3000].split(",")[:24] if keys is not None else None,
            user=self.request.user,
            queryset=queryset,
        )
        if self.request.query_params.get("mine") == "true":
            icons = icons.filter(created_by=self.request.user)
        return super().filter_queryset(icons)


class IconDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Icon.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = IconDetailSerializer
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def filter_queryset(self, queryset):
        return super().filter_queryset(queryset.filter(created_by=self.request.user))

    def perform_destroy(self, instance):
        artwork = instance.file
        instance.delete()
        artwork.delete(save=False)
