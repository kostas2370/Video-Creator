from rest_framework import serializers

from apps.videomanagement.serializers.fields import FiniteFloat

SHOT_SIZES = ("WIDE", "MEDIUM", "CLOSE_UP", "DETAIL")
CAMERA_MOVEMENTS = (
    "STATIC",
    "PAN_LEFT",
    "PAN_RIGHT",
    "TILT_UP",
    "TILT_DOWN",
    "PUSH_IN",
    "PULL_OUT",
)
STILL_MOTION = {
    "STATIC": "NONE",
    "PAN_LEFT": "PAN_LEFT",
    "PAN_RIGHT": "PAN_RIGHT",
    "TILT_UP": "PAN_UP",
    "TILT_DOWN": "PAN_DOWN",
    "PUSH_IN": "ZOOM_IN",
    "PULL_OUT": "ZOOM_OUT",
}


class ShotPlanSerializer(serializers.Serializer):
    shot_size = serializers.ChoiceField(
        choices=SHOT_SIZES, required=False, allow_blank=True
    )
    camera_movement = serializers.ChoiceField(
        choices=CAMERA_MOVEMENTS, required=False, allow_blank=True
    )
    subject_action = serializers.CharField(
        required=False, allow_blank=True, max_length=500
    )
    target_duration = FiniteFloat(
        required=False, allow_null=True, min_value=0.5, max_value=30
    )
