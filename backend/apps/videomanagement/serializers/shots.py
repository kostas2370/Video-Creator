from rest_framework import serializers

from apps.videomanagement.models import MotionIntensity, MotionStyle
from .fields import FiniteFloat


class ShotSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    timing_weight = FiniteFloat(min_value=0.000001, max_value=900, default=1)
    trim_start = FiniteFloat(min_value=0, max_value=900, default=0)
    motion_style = serializers.ChoiceField(
        choices=MotionStyle.choices, allow_null=True, default=None
    )
    motion_intensity = serializers.ChoiceField(
        choices=MotionIntensity.choices, allow_null=True, default=None
    )
    with_audio = serializers.BooleanField(default=False)


class SceneShotsSerializer(serializers.Serializer):
    expected_ids = serializers.ListField(child=serializers.UUIDField(), max_length=20)
    shots = ShotSerializer(many=True, allow_empty=False, max_length=20)

    def validate(self, attrs):
        ids = [shot["id"] for shot in attrs["shots"]]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError("Each shot must appear only once.")
        return attrs
