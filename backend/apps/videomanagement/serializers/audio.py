from rest_framework import serializers

from apps.common.youtube import youtube_url
from apps.videomanagement.models import Music

from .fields import FiniteFloat as FiniteFloat


class MusicDetailsSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    artist = serializers.SerializerMethodField()
    source_url = serializers.URLField(
        source="catalog_track.source_url", default="", read_only=True
    )
    license_url = serializers.URLField(
        source="catalog_track.license_url", default="", read_only=True
    )
    attribution = serializers.CharField(
        source="catalog_track.attribution", default="", read_only=True
    )

    class Meta:
        model = Music
        fields = ("title", "artist", "file", "source_url", "license_url", "attribution")
        read_only_fields = fields

    def get_title(self, obj):
        return obj.catalog_track.title if obj.catalog_track else obj.name

    def get_artist(self, obj):
        if not obj.catalog_track:
            return ""
        metadata = obj.catalog_track.metadata
        return metadata.get("artist") or metadata.get("channel_title") or ""


class SceneAudioSerializer(serializers.Serializer):
    trim_start = FiniteFloat(min_value=0, max_value=900, required=False)
    trim_end = FiniteFloat(min_value=0, max_value=900, required=False, allow_null=True)
    delay = FiniteFloat(min_value=0, max_value=60, required=False)
    fade_in = FiniteFloat(min_value=0, max_value=30, required=False)
    fade_out = FiniteFloat(min_value=0, max_value=30, required=False)
    crossfade = FiniteFloat(min_value=0, max_value=10, required=False)
    volume = FiniteFloat(min_value=0, max_value=1, required=False)


class MusicAudioSerializer(serializers.Serializer):
    music_ducking = serializers.BooleanField(required=False)
    music_volume = FiniteFloat(min_value=0, max_value=1, required=False)
    music_fade_in = FiniteFloat(min_value=0, max_value=30, required=False)
    music_fade_out = FiniteFloat(min_value=0, max_value=30, required=False)
    duck_level = FiniteFloat(min_value=0, max_value=1, required=False)
    duck_attack = FiniteFloat(min_value=0.05, max_value=5, required=False)
    duck_release = FiniteFloat(min_value=0.05, max_value=5, required=False)


class VoiceoverUploadSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, value):
        if value.size > 50 * 1024 * 1024:
            raise serializers.ValidationError("Audio must be smaller than 50 MB.")
        return value


class MusicUploadSerializer(VoiceoverUploadSerializer):
    file = serializers.FileField(required=False)
    youtube_url = serializers.CharField(required=False, max_length=2048)

    def validate_youtube_url(self, value):
        return youtube_url(value)

    def validate(self, attrs):
        if ("file" in attrs) == ("youtube_url" in attrs):
            raise serializers.ValidationError("Choose an audio file or a YouTube link.")
        return attrs
