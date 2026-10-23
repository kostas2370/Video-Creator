from django.utils import timezone
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny

from .models import NewsUpdate
from .serializers import NewsUpdateSerializer


class NewsUpdatePagination(PageNumberPagination):
    page_size = 10


class NewsUpdateListView(ListAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = NewsUpdateSerializer
    pagination_class = NewsUpdatePagination

    def get_queryset(self):
        return NewsUpdate.objects.filter(
            status=NewsUpdate.Status.PUBLISHED, published_at__lte=timezone.now()
        )
