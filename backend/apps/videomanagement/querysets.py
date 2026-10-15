from django.db import models
from django.db.models import Count, Min, Q, Sum


class AIUsageQuerySet(models.QuerySet):
    def first_recorded_at(self):
        return self.aggregate(first=Min("created_at"))["first"]

    def summary(self):
        """Aggregate only this queryset's records into totals and grouped rows."""
        metrics = {
            # Resolve this filter before the total_tokens aggregation shadows the field.
            "requests_with_tokens": Count("id", filter=Q(total_tokens__isnull=False)),
            "requests": Count("id"),
            "input_tokens": Sum("input_tokens", default=0),
            "output_tokens": Sum("output_tokens", default=0),
            "total_tokens": Sum("total_tokens", default=0),
            "characters": Sum("characters", default=0),
            "images": Sum("images", default=0),
            "seconds": Sum("seconds", default=0),
        }
        grouping = ("service", "provider", "model", "key_source")
        return {
            "totals": self.aggregate(**metrics),
            "breakdown": list(
                self.values(*grouping).annotate(**metrics).order_by(*grouping)
            ),
        }
