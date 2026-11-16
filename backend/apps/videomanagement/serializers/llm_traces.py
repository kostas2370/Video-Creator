from rest_framework import serializers

from apps.usage.models import LLMTrace


class LLMTraceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LLMTrace
        fields = [
            "id",
            "created_at",
            "model",
            "attempt",
            "prompt",
            "response",
            "validation_errors",
            "has_reference_image",
        ]
        read_only_fields = fields
