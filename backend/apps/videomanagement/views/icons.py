from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from apps.videomanagement.paginator import AssetResultsPagination
from apps.videomanagement.serializers.icons import IconSerializer
from apps.videomanagement.services.media.icons import search_icons


class IconListView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = IconSerializer
    pagination_class = AssetResultsPagination

    def get_queryset(self):
        keys = self.request.query_params.get("keys")
        return search_icons(self.request.query_params.get("search", "")[:300],
                            keys=keys[:3000].split(",")[:24] if keys is not None else None,
                            user=self.request.user)
