from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from django_filters import rest_framework as filters

from .models import AIUsage, MediaAsset, Video, VideoType


class UsageFilter(filters.FilterSet):
    period = filters.ChoiceFilter(
        choices=[("7", "Last 7 days"), ("30", "Last 30 days"), ("all", "All time")],
        method="filter_period",
        required=True,
    )

    class Meta:
        model = AIUsage
        fields = ["period"]

    def __init__(self, data=None, *args, **kwargs):
        data = data.copy() if data is not None else {}
        data.setdefault("period", "30")
        super().__init__(data, *args, **kwargs)

    def filter_period(self, queryset, name, value):
        if value == "all":
            return queryset
        return queryset.filter(
            created_at__gte=timezone.now() - timedelta(days=int(value))
        )


class MediaAssetFilter(filters.FilterSet):
    search = filters.CharFilter(method="filter_search")
    kind = filters.ChoiceFilter(
        choices=[*MediaAsset.Kind.choices, ("VISUAL", "Images and video")],
        method="filter_kind",
    )

    class Meta:
        model = MediaAsset
        fields = ("search", "kind")

    def filter_search(self, queryset, name, value):
        term = value.strip()[:100]
        return (
            queryset.filter(Q(title__icontains=term) | Q(tags__icontains=term))
            if term
            else queryset
        )

    def filter_kind(self, queryset, name, value):
        if value == "VISUAL":
            return queryset.filter(
                kind__in=(MediaAsset.Kind.IMAGE, MediaAsset.Kind.VIDEO)
            )
        return queryset.filter(kind=value)


class VideoFilter(filters.FilterSet):
    creation_mode = filters.ChoiceFilter(
        choices=[
            ("AI", "AI video"),
            ("MANUAL", "Manual edit"),
            ("STORY", "Story video"),
            ("SERIES", "Series episode"),
        ],
        method="filter_creation_mode",
    )
    is_favorite = filters.BooleanFilter()
    ordering = filters.OrderingFilter(
        fields=("updated_at", "created_at", "title"), method="filter_ordering"
    )

    class Meta:
        model = Video
        fields = ("status", "video_type", "creation_mode", "is_favorite")

    def filter_creation_mode(self, queryset, name, value):
        if value in ("STORY", "SERIES"):
            return queryset.filter(settings__creation_mode=value)
        # Older projects may have null settings or no creation_mode key.
        return queryset.filter(video_type=VideoType(value)).filter(
            Q(settings__creation_mode__isnull=True)
            | ~Q(settings__creation_mode__in=("STORY", "SERIES"))
        )

    def filter_ordering(self, queryset, name, value):
        return queryset.order_by(*value, "id")
