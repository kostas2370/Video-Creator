"""Motion fields shared by editor requests and storyboard plans."""

from rest_framework import serializers

from ..models import MotionIntensity, PhotoAnimation


class MotionSettingsSerializer(serializers.Serializer):
    motion_intensity = serializers.ChoiceField(
        choices=MotionIntensity.choices, required=False
    )
    animation_preset = serializers.ChoiceField(
        choices=PhotoAnimation.choices, default="NONE"
    )
    animation_accents = serializers.BooleanField(required=False)
