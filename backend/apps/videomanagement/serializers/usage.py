from django.db.models import Count, Min, Q, Sum
from drf_yasg.utils import swagger_serializer_method
from rest_framework import serializers


def usage_metrics():
    return {
        "requests_with_tokens": Count("id", filter=Q(total_tokens__isnull=False)),
        "requests": Count("id"),
        "input_tokens": Sum("input_tokens", default=0),
        "output_tokens": Sum("output_tokens", default=0),
        "total_tokens": Sum("total_tokens", default=0),
        "characters": Sum("characters", default=0),
        "images": Sum("images", default=0),
        "seconds": Sum("seconds", default=0),
    }


class UsageMetricsSerializer(serializers.Serializer):
    requests = serializers.IntegerField()
    requests_with_tokens = serializers.IntegerField()
    input_tokens = serializers.IntegerField()
    output_tokens = serializers.IntegerField()
    total_tokens = serializers.IntegerField()
    characters = serializers.IntegerField()
    images = serializers.IntegerField()
    seconds = serializers.IntegerField()


class UsageBreakdownSerializer(UsageMetricsSerializer):
    service = serializers.CharField()
    provider = serializers.CharField()
    model = serializers.CharField(allow_blank=True)
    key_source = serializers.CharField()


class UsageSerializer(serializers.Serializer):
    period = serializers.CharField()
    first_recorded_at = serializers.SerializerMethodField()
    totals = serializers.SerializerMethodField()
    breakdown = serializers.SerializerMethodField()

    @swagger_serializer_method(
        serializer_or_field=serializers.DateTimeField(allow_null=True)
    )
    def get_first_recorded_at(self, instance):
        first = instance["all_usage"].aggregate(first=Min("created_at"))["first"]
        return serializers.DateTimeField().to_representation(first) if first else None

    @swagger_serializer_method(serializer_or_field=UsageMetricsSerializer)
    def get_totals(self, instance):
        totals = instance["usage"].aggregate(**usage_metrics())
        return UsageMetricsSerializer(totals).data

    @swagger_serializer_method(serializer_or_field=UsageBreakdownSerializer(many=True))
    def get_breakdown(self, instance):
        grouping = ("service", "provider", "model", "key_source")
        breakdown = (
            instance["usage"]
            .values(*grouping)
            .annotate(**usage_metrics())
            .order_by(*grouping)
        )
        return UsageBreakdownSerializer(breakdown, many=True).data
