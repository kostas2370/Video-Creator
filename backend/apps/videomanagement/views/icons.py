from rest_framework import generics, serializers
from rest_framework.permissions import IsAuthenticated

from apps.videomanagement.models import Icon
from apps.videomanagement.paginator import AssetResultsPagination
from apps.videomanagement.services.media.icons import search_icons


class IconSerializer(serializers.ModelSerializer):
    class Meta:
        model = Icon
        fields = ("key", "collection", "name", "description", "file", "license", "license_url", "attribution")


class IconListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = IconSerializer
    pagination_class = AssetResultsPagination

    def get_queryset(self):
        keys = self.request.query_params.get("keys")
        return search_icons(self.request.query_params.get("search", "")[:300],
                            keys=keys[:3000].split(",")[:24] if keys is not None else None)
