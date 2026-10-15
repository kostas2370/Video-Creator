from rest_framework import serializers


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
    first_recorded_at = serializers.DateTimeField(allow_null=True)
    totals = UsageMetricsSerializer()
    breakdown = UsageBreakdownSerializer(many=True)
