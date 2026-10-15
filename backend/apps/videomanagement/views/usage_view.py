from django.db.models import Count, Min, Q, Sum
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..filters import UsageFilter
from ..models import AIUsage
from ..serializers.usage import UsageSerializer


class UsageView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UsageSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = UsageFilter

    def get_queryset(self):
        return AIUsage.objects.filter(user=self.request.user)

    @swagger_auto_schema(responses={200: UsageSerializer})
    def get(self, request):
        all_usage = self.get_queryset()
        usage = self.filter_queryset(all_usage)
        period = request.query_params.get("period", "30")
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
        serializer = self.get_serializer(
            {
                "period": period,
                "first_recorded_at": all_usage.aggregate(first=Min("created_at"))[
                    "first"
                ],
                "totals": usage.aggregate(**metrics),
                "breakdown": breakdown,
            }
        )
        return Response(serializer.data)
