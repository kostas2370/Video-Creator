"""The supported editing settings an AI storyboard may propose."""

from rest_framework import serializers

from apps.videomanagement.models import MotionIntensity, MotionStyle, PhotoAnimation, TransitionStyle
from apps.videomanagement.serializers.fields import FiniteFloat


class PlannedOverlaySerializer(serializers.Serializer):
    """Reviewable label timing, expressed as a fraction of the finished scene."""

    text = serializers.CharField(max_length=80)
    position = serializers.ChoiceField(
        choices=("top-left", "top-center", "top-right", "middle-center"),
        default="top-center",
    )
    start_fraction = FiniteFloat(min_value=0, max_value=1)
    end_fraction = FiniteFloat(min_value=0, max_value=1)

    def validate(self, attrs):
        if attrs["end_fraction"] <= attrs["start_fraction"]:
            raise serializers.ValidationError("The label must end after it starts.")
        return attrs


class SceneEditingPlanSerializer(serializers.Serializer):
    motion_style = serializers.ChoiceField(choices=MotionStyle.choices)
    motion_intensity = serializers.ChoiceField(choices=MotionIntensity.choices)
    transition_after = serializers.ChoiceField(choices=TransitionStyle.choices)
    transition_duration = FiniteFloat(min_value=0.1, max_value=0.6)
    pause_after = FiniteFloat(min_value=0, max_value=0.8)
    animation_preset = serializers.ChoiceField(choices=PhotoAnimation.choices, required=False)
    animation_accents = serializers.BooleanField(required=False)
    overlays = PlannedOverlaySerializer(many=True, required=False, max_length=2)

    def validate(self, attrs):
        if self.context.get("video_provider") and attrs["motion_style"] != MotionStyle.NONE:
            raise serializers.ValidationError("Use NONE motion for video providers.")
        if self.context.get("video_provider") and attrs.get("animation_preset", "NONE") != "NONE":
            raise serializers.ValidationError("Use NONE photo animation for video providers.")
        overlays = sorted(attrs.get("overlays", []), key=lambda item: item["start_fraction"])
        if any(left["end_fraction"] > right["start_fraction"] for left, right in zip(overlays, overlays[1:])):
            raise serializers.ValidationError("Show one planned label at a time.")
        return attrs
