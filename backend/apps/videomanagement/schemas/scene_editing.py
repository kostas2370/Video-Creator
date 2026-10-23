"""The supported editing settings an AI storyboard may propose."""

from rest_framework import serializers

from apps.videomanagement.models import MotionIntensity, MotionStyle, TransitionStyle
from apps.videomanagement.serializers.fields import FiniteFloat


class SceneEditingPlanSerializer(serializers.Serializer):
    motion_style = serializers.ChoiceField(choices=MotionStyle.choices)
    motion_intensity = serializers.ChoiceField(choices=MotionIntensity.choices)
    transition_after = serializers.ChoiceField(choices=TransitionStyle.choices)
    transition_duration = FiniteFloat(min_value=0.1, max_value=0.6)
    pause_after = FiniteFloat(min_value=0, max_value=0.8)

    def validate(self, attrs):
        if self.context.get("video_provider") and attrs["motion_style"] != MotionStyle.NONE:
            raise serializers.ValidationError("Use NONE motion for video providers.")
        return attrs
