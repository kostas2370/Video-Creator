from datetime import timedelta

from django.utils import timezone
from django_filters import rest_framework as filters

from .models import AIUsage


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
