from datetime import timedelta

from django.utils import timezone
from django_filters import rest_framework as filters

from apps.common.filters import UserFilterSet

from .models import AIUsage


class UsageFilter(UserFilterSet):
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


class ProjectUsageFilter(UserFilterSet):
    def scope_queryset(self, queryset):
        context = self.request.parser_context
        return (
            super()
            .scope_queryset(queryset)
            .filter(
                video_id=context["kwargs"]["video_id"],
                service__in=("text", "images", "tts", "video"),
            )
        )
