from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny

from .filters import NewsUpdateFilter
from .models import NewsUpdate
from .serializers import NewsUpdateSerializer


class NewsUpdatePagination(PageNumberPagination):
    page_size = 10


class NewsUpdateListView(ListAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = NewsUpdateSerializer
    pagination_class = NewsUpdatePagination

    queryset = NewsUpdate.objects.all()
    filter_backends = [DjangoFilterBackend]
    filterset_class = NewsUpdateFilter
