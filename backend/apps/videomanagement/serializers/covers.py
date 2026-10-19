from rest_framework import serializers

from apps.videomanagement.utils.captions.styles import FONTS

from .audio import FiniteFloat


class CoverSerializer(serializers.Serializer):
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
