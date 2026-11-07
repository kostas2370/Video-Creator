from rest_framework import serializers


class ImageReviewRequestSerializer(serializers.Serializer):
    asset_id = serializers.UUIDField()


class ImageReviewFindingSerializer(serializers.Serializer):
    category = serializers.ChoiceField(
        choices=["character", "shot", "composition", "quality"]
    )
    issue = serializers.CharField(max_length=500)
    fix = serializers.CharField(max_length=500)


class ImageReviewResultSerializer(serializers.Serializer):
    verdict = serializers.ChoiceField(choices=["ready", "needs_changes", "uncertain"])
    summary = serializers.CharField(max_length=800)
    findings = ImageReviewFindingSerializer(many=True, max_length=6)
    suggested_description = serializers.CharField(max_length=2000, allow_blank=True)

    def validate(self, attrs):
        if attrs["verdict"] == "ready" and attrs["findings"]:
            raise serializers.ValidationError("A ready image cannot have findings.")
        if attrs["verdict"] == "needs_changes" and not attrs["findings"]:
            raise serializers.ValidationError("Describe the changes needed.")
        return attrs
