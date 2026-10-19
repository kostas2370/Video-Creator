from rest_framework import serializers

from .caption_words import CaptionWordSerializer


class SceneCaptionsSerializer(serializers.Serializer):
    revision = serializers.RegexField(r"^[a-f0-9]{64}$")
    words = CaptionWordSerializer(many=True, max_length=10000)
