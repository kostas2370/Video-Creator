import math

from rest_framework import serializers

from apps.videomanagement.utils.captions.styles import CAPTION_STYLES, FONTS


class CaptionPresetField(serializers.ChoiceField):
    def __init__(self, **kwargs):
        super().__init__(choices=(*CAPTION_STYLES, "CUSTOM"), **kwargs)


class CaptionStyleSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=50, required=False)
    font = serializers.ChoiceField(choices=FONTS, required=False)
    font_size = serializers.FloatField(min_value=1, max_value=15, required=False)
    color = serializers.RegexField(r"^#[0-9a-fA-F]{6}$", required=False)
    highlight_color = serializers.RegexField(r"^#[0-9a-fA-F]{6}$", required=False)
    outline_color = serializers.RegexField(r"^#[0-9a-fA-F]{6}$", required=False)
    outline_width = serializers.FloatField(min_value=0, max_value=1.5, required=False)
    shadow = serializers.FloatField(min_value=0, max_value=1, required=False)
    bold = serializers.BooleanField(required=False)
    uppercase = serializers.BooleanField(required=False)
    highlight_words = serializers.BooleanField(required=False)
    position = serializers.ChoiceField(
        choices=("bottom", "middle", "top"), required=False
    )
    margin_left = serializers.FloatField(min_value=0, max_value=30, required=False)
    margin_right = serializers.FloatField(min_value=0, max_value=30, required=False)
    margin_vertical = serializers.FloatField(min_value=0, max_value=40, required=False)
    portrait_margin_vertical = serializers.FloatField(
        min_value=0, max_value=40, required=False
    )
    line_width = serializers.IntegerField(min_value=8, max_value=48, required=False)
    max_words = serializers.IntegerField(min_value=1, max_value=15, required=False)
    max_characters = serializers.IntegerField(
        min_value=10, max_value=100, required=False
    )

    def validate(self, data):
        if any(
            isinstance(value, float) and not math.isfinite(value)
            for value in data.values()
        ):
            raise serializers.ValidationError(
                "Style sizes and margins must be finite numbers."
            )
        # Custom sizes use a percentage of the shorter frame dimension.
        # Raw ASS/CSS and font-file paths are never accepted.
        return data

    def to_internal_value(self, data):
        if isinstance(data, dict):
            unknown = set(data) - set(self.fields)
            if unknown:
                raise serializers.ValidationError(
                    "Unsupported caption style fields: " + ", ".join(sorted(unknown))
                )
        return super().to_internal_value(data)
