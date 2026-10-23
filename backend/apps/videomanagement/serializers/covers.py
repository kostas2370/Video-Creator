from rest_framework import serializers

from apps.videomanagement.utils.captions.styles import FONTS

from .fields import FiniteFloat, validate_image_upload


class CoverSerializer(serializers.Serializer):
    source = serializers.ChoiceField(choices=("frame", "ai", "upload"), default="frame")
    image = serializers.ImageField(required=False, write_only=True)
    time = FiniteFloat(min_value=0, max_value=86400, default=0)
    title = serializers.CharField(
        max_length=100, allow_blank=True, default="", trim_whitespace=False
    )
    font = serializers.ChoiceField(choices=FONTS, default="Poppins")
    color = serializers.RegexField(r"^#[0-9a-fA-F]{6}$", default="#ffffff")
    position = serializers.ChoiceField(
        choices=("top", "middle", "bottom"), default="bottom"
    )
    size = FiniteFloat(min_value=3, max_value=16, default=8)
    background = serializers.BooleanField(default=True)

    def validate_image(self, image):
        return validate_image_upload(
            image,
            max_pixels=20_000_000,
            messages={
                "format": "Choose a PNG, JPEG, or WebP image.",
                "size": "Choose an image smaller than 10 MB.",
                "pixels": "Choose an image smaller than 20 megapixels.",
            },
        )

    def validate(self, data):
        if data["source"] != "frame" and "image" not in data:
            raise serializers.ValidationError(
                {"image": "Generate or upload an image first."}
            )
        return data


class GenerateCoverSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=100, allow_blank=True, default="")
    prompt = serializers.CharField(max_length=1500, allow_blank=True, default="")
    time = FiniteFloat(min_value=0, max_value=86400, default=0)
