from django.conf import settings
from rest_framework import serializers

from apps.videomanagement.services.media.music_discovery import TARGETS


class MusicSearchSerializer(serializers.Serializer):
    video_id = serializers.UUIDField(required=False)
    prompt = serializers.CharField(
        max_length=2000, required=False, allow_blank=True, default=""
    )
    genre = serializers.CharField(max_length=100, allow_blank=True, default="")
    gpt_model = serializers.ChoiceField(
        choices=settings.ACCEPTED_MODELS, allow_blank=True, default=""
    )
    preferences = serializers.CharField(max_length=500, allow_blank=True, default="")

    def validate(self, attrs):
        if not attrs.get("video_id") and not attrs["prompt"].strip():
            raise serializers.ValidationError(
                "Describe your video before searching for music."
            )
        return attrs


class MusicBriefSerializer(serializers.Serializer):
    mood = serializers.CharField(max_length=100)
    instruments = serializers.CharField(max_length=100)
    tempo = serializers.CharField(max_length=100)
    category = serializers.ChoiceField(choices=list(TARGETS))
    query = serializers.CharField(max_length=200)

    def to_internal_value(self, data):
        if isinstance(data, dict):
            data = dict(data)
            for field in ("mood", "instruments", "tempo"):
                value = data.get(field)
                if isinstance(value, list) and all(
                    isinstance(item, str) for item in value
                ):
                    data[field] = ", ".join(value)
        return super().to_internal_value(data)


class RankedMusicSerializer(serializers.Serializer):
    key = serializers.CharField(max_length=80)
    reason = serializers.CharField(max_length=240)


class MusicRankingSerializer(serializers.Serializer):
    tracks = RankedMusicSerializer(many=True, max_length=5)


class MusicImportSerializer(serializers.Serializer):
    video_id = serializers.UUIDField()
    selection = serializers.RegexField(
        r"^(?:ai:[A-Za-z0-9_-]{11}|catalog:[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})$"
    )
