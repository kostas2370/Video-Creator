from rest_framework import serializers


class UsageMetricsSerializer(serializers.Serializer):
    cost_usd = serializers.DecimalField(
        max_digits=16, decimal_places=8, allow_null=True
    )
    requests_with_cost = serializers.IntegerField()
    requests = serializers.IntegerField()
    requests_with_input_tokens = serializers.IntegerField()
    requests_with_output_tokens = serializers.IntegerField()
    requests_with_tokens = serializers.IntegerField()
    input_tokens = serializers.IntegerField(allow_null=True)
    output_tokens = serializers.IntegerField(allow_null=True)
    total_tokens = serializers.IntegerField(allow_null=True)
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


class CostEstimateRequestSerializer(serializers.Serializer):
    video_id = serializers.UUIDField()
    storyboard = serializers.DictField(required=False)
    scene_id = serializers.UUIDField(required=False)
    operation = serializers.ChoiceField(
        choices=("all", "visual", "animation", "narration"), default="all"
    )
    text = serializers.CharField(
        required=False, allow_blank=True, max_length=2000, trim_whitespace=False
    )

    def validate_storyboard(self, value):
        from apps.videomanagement.serializers.requests import StoryboardSerializer

        serializer = StoryboardSerializer(data=value, context={"narration": False})
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data


class ScenarioEstimateRequestSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=2000)
    gpt_model = serializers.CharField(max_length=100, required=False, allow_blank=True)
    scene_count = serializers.IntegerField(
        min_value=1, max_value=60, required=False, allow_null=True
    )
    genre = serializers.CharField(max_length=100, required=False, allow_blank=True)
    target_audience = serializers.CharField(
        max_length=2000, required=False, allow_blank=True
    )
    platform = serializers.CharField(max_length=30, required=False)
    image_mode = serializers.ChoiceField(choices=("WEB", "AI"), required=False)
    provider = serializers.CharField(max_length=100, required=False, allow_blank=True)
    style = serializers.CharField(max_length=200, required=False, allow_blank=True)
    narration = serializers.BooleanField(required=False)
    ai_scene_editing = serializers.BooleanField(required=False)
    visual_continuity = serializers.CharField(
        max_length=3000, required=False, allow_blank=True
    )
    reference_role = serializers.ChoiceField(
        choices=("both", "style", "character"), required=False
    )
    has_reference = serializers.BooleanField(required=False)
