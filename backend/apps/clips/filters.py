from django.db.models import Count, Q
from django_filters import rest_framework as filters

from apps.common.filters import OwnerFilterSet

from .choices import PROJECT_BUSY, ClipStatus


class ClipProjectFilter(OwnerFilterSet):
    search = filters.CharFilter(method="filter_search")
    status = filters.CharFilter(method="filter_status")

    def scope_queryset(self, queryset):
        rows = super().scope_queryset(queryset).defer("transcript_parts")
        if self.action == "list":
            return (
                rows.defer("words")
                .annotate(
                    clip_total=Count("clips"),
                    export_total=Count(
                        "clips", filter=Q(clips__status=ClipStatus.COMPLETED)
                    ),
                )
                .order_by("-created_at", "-id")
            )
        if self.action == "retrieve":
            rows = rows.prefetch_related("clips")
        return rows

    def filter_search(self, queryset, name, value):
        term = value.strip()[:200]
        return (
            queryset.filter(title__icontains=term)
            if self.action == "list" and term
            else queryset
        )

    def filter_status(self, queryset, name, value):
        if self.action != "list":
            return queryset
        return (
            queryset.filter(status__in=PROJECT_BUSY)
            if value == "PROCESSING"
            else queryset.filter(status=value)
        )
