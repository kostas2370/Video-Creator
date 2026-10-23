from rest_framework import serializers

from .fields import FiniteFloat as FiniteFloat


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
