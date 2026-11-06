from django.utils import timezone

from apps.common.filters import BaseFilterSet

from .models import NewsUpdate


class NewsUpdateFilter(BaseFilterSet):
    def scope_queryset(self, queryset):
        return queryset.filter(
            status=NewsUpdate.Status.PUBLISHED, published_at__lte=timezone.now()
        )
