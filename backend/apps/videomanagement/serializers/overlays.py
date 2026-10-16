"""Bounded, provider-independent scene overlay settings."""

import math

from rest_framework import serializers

POSITIONS = (
    "top-left",
    "top-center",
    "top-right",
    "middle-left",
    "middle-center",
    "middle-right",
    "bottom-left",
    "bottom-center",
    "bottom-right",
)


class OverlaySerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=("title", "lower-third", "watermark", "cta"))
    text = serializers.CharField(max_length=200, allow_blank=True, default="")
    logo = serializers.BooleanField(default=False)
    position = serializers.ChoiceField(choices=POSITIONS, default="middle-center")
    start = serializers.FloatField(min_value=0, max_value=86400, default=0)
    end = serializers.FloatField(
        min_value=0, max_value=86400, allow_null=True, default=None
    )
    size = serializers.FloatField(min_value=2, max_value=8, default=4)
    width = serializers.FloatField(min_value=5, max_value=50, default=20)
    color = serializers.RegexField(r"^#[0-9a-fA-F]{6}$", default="#ffffff")
    background = serializers.BooleanField(default=True)
    opacity = serializers.FloatField(min_value=0.1, max_value=1, default=1)

    def validate(self, data):
        if any(
            not math.isfinite(data[key])
            for key in ("start", "size", "width", "opacity")
        ) or (data["end"] is not None and not math.isfinite(data["end"])):
            raise serializers.ValidationError(
                "Enter finite numbers for overlay settings."
            )
        if data["end"] is not None and data["end"] <= data["start"]:
            raise serializers.ValidationError("The end must be after the start.")
        if not data["logo"] and not data["text"].strip():
            raise serializers.ValidationError(
                "Enter overlay text or select a watermark logo."
            )
        if data["logo"] and data["kind"] != "watermark":
            raise serializers.ValidationError("Only watermarks can use the logo.")
        return data


class SceneOverlaysSerializer(serializers.Serializer):
    # JSONField also decodes the JSON string in a multipart request with a logo.
    overlays = serializers.JSONField()
    overlay_logo = serializers.ImageField(required=False)

    def validate_overlays(self, value):
        if not isinstance(value, list) or len(value) > 8:
            raise serializers.ValidationError("Use at most eight overlays per scene.")
        serializer = OverlaySerializer(data=value, many=True)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data

    def validate_overlay_logo(self, value):
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("Use a logo smaller than 10 MB.")
        if value.image.width * value.image.height > 16_000_000:
            raise serializers.ValidationError(
                "Use a logo with at most 16 million pixels."
            )
        if value.image.format not in ("PNG", "JPEG", "WEBP"):
            raise serializers.ValidationError("Use a PNG, JPEG or WebP logo.")
        if getattr(value.image, "is_animated", False):
            raise serializers.ValidationError("Use a still image for your logo.")
        return value
