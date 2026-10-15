from datetime import timedelta

from django.db.models import Count, Min, Q, Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import AIUsage


class UsageView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        period = request.query_params.get("period", "30")
        if period not in ("7", "30", "all"):
            raise ValidationError({"period": "Choose 7, 30, or all."})
        all_usage = AIUsage.objects.filter(user=request.user)
        usage = all_usage
        if period != "all":
            usage = usage.filter(
                created_at__gte=timezone.now() - timedelta(days=int(period))
            )
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
        breakdown = list(
            usage.values("service", "provider", "model", "key_source")
            .annotate(**metrics)
            .order_by("service", "provider", "model", "key_source")
        )
        return Response(
            {
                "period": period,
                "first_recorded_at": all_usage.aggregate(first=Min("created_at"))[
                    "first"
                ],
                "totals": usage.aggregate(**metrics),
                "breakdown": breakdown,
            }
        )
