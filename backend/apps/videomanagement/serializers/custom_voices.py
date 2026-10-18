from rest_framework import serializers

from .models import VoiceModelSerializer


class CloneVoiceSerializer(VoiceModelSerializer):
    name = serializers.CharField(max_length=80)
    file = serializers.FileField(write_only=True)
    consent = serializers.BooleanField(write_only=True)

    class Meta(VoiceModelSerializer.Meta):
        fields = (*VoiceModelSerializer.Meta.fields, "file", "consent")

    def validate_consent(self, value):
        if not value:
            raise serializers.ValidationError("Confirm that this is your voice and you consent to cloning it.")
        return value

    def validate_file(self, value):
        if value.size > 20 * 1024 * 1024:
            raise serializers.ValidationError("Audio must be smaller than 20 MB.")
        return value
