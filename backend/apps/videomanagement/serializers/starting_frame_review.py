from rest_framework import serializers

from .fields import StrictCharField


class StartingFrameReviewRequestSerializer(serializers.Serializer):
    asset_id = serializers.UUIDField()


class StartingFrameReviewFindingSerializer(serializers.Serializer):
    category = serializers.ChoiceField(
        choices=["character", "shot", "composition", "quality"]
    )
    issue = StrictCharField(max_length=500)
    fix = StrictCharField(max_length=500)


class StartingFrameReviewResultSerializer(serializers.Serializer):
    verdict = serializers.ChoiceField(choices=["ready", "needs_changes", "uncertain"])
    summary = StrictCharField(max_length=800)
    findings = StartingFrameReviewFindingSerializer(many=True, max_length=6)
    suggested_description = StrictCharField(max_length=2000, allow_blank=True)

    def validate(self, attrs):
        if attrs["verdict"] == "ready" and attrs["findings"]:
            raise serializers.ValidationError("A ready image cannot have findings.")
        if attrs["verdict"] == "needs_changes" and not attrs["findings"]:
            raise serializers.ValidationError("Describe the changes needed.")
        return attrs
