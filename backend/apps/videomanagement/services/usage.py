from django.db.models import Count, Min, Q, Sum


def summarize_usage(all_usage, usage, *, period):
    """Summarize an owner-scoped queryset and its filtered reporting period."""
    metrics = {
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
        "period": period,
        "first_recorded_at": all_usage.aggregate(first=Min("created_at"))["first"],
        "totals": usage.aggregate(**metrics),
        "breakdown": list(
            usage.values(*grouping).annotate(**metrics).order_by(*grouping)
        ),
    }
