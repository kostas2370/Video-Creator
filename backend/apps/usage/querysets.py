from django.db import models
from django.db.models import Count, Min, Q, Sum

TOKEN_METRICS = {
    "input_tokens": "requests_with_input_tokens",
    "output_tokens": "requests_with_output_tokens",
    "total_tokens": "requests_with_tokens",
}


class AIUsageQuerySet(models.QuerySet):
    def first_recorded_at(self):
        return self.aggregate(first=Min("created_at"))["first"]

    def summary(self):
        """Aggregate this selection, preserving unknown and partially reported counts."""
        # Count availability before sum aliases shadow their source fields.
        metrics = {
            coverage: Count("id", filter=Q(**{f"{field}__isnull": False}))
            for field, coverage in TOKEN_METRICS.items()
        }
        metrics["requests"] = Count("id")
        metrics["requests_with_cost"] = Count("id", filter=Q(cost_usd__isnull=False))
        metrics["cost_usd"] = Sum("cost_usd")
        metrics.update(
            {
                field: Sum(field, default=0)
                for field in (*TOKEN_METRICS, "characters", "images", "seconds")
            }
        )

        def preserve_unknowns(row):
            if not row["requests"]:
                row["cost_usd"] = 0
            for field, coverage in TOKEN_METRICS.items():
                if row["requests"] and not row[coverage]:
                    row[field] = None
            return row

        grouping = ("service", "provider", "model", "key_source")
        return {
            "totals": preserve_unknowns(self.aggregate(**metrics)),
            "breakdown": [
                preserve_unknowns(row)
                for row in self.values(*grouping)
                .annotate(**metrics)
                .order_by(*grouping)
            ],
        }
