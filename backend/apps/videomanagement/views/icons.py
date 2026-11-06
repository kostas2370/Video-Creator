from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from apps.common.filters import OwnerFilterSet
from apps.videomanagement.filters import IconFilter
from apps.videomanagement.models import Icon
from apps.videomanagement.paginator import AssetResultsPagination
from apps.videomanagement.serializers.icons import IconDetailSerializer, IconSerializer


class IconListView(generics.ListCreateAPIView):
    queryset = Icon.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = IconSerializer
    pagination_class = AssetResultsPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = IconFilter



class IconDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Icon.objects.all()
    filter_backends = [DjangoFilterBackend]
    filterset_class = OwnerFilterSet
    permission_classes = [IsAuthenticated]
    serializer_class = IconDetailSerializer
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def perform_destroy(self, instance):
        artwork = instance.file
        instance.delete()
        artwork.delete(save=False)
