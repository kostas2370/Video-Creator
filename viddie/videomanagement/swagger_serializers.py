from rest_framework import serializers
from .models import TEMPLATE_CHOICES


class GenerateSerializer(serializers.Serializer):
    prompt = serializers.CharField(required = True, max_length = 2000)
    template_select = serializers.CharField(required = False, max_length = 20)
    voice_Id = serializers.CharField(required = False, max_length = 20)
    gpt_model = serializers.CharField(required = False, max_length = 30)
    images = serializers.CharField(required = False, max_length = 30)
    avatar_selection = serializers.CharField(required = False, max_length = 30)
    style = serializers.CharField(required = False, max_length = 30)
    music = serializers.CharField(required = False, max_length = 80)
    target_audience = serializers.CharField(required = False, max_length = 30)


class DownloadPlaylistSerializer(serializers.Serializer):
    link = serializers.URLField(required = True)
    category = serializers.CharField(max_length = 30)

    def validate_category(self, value):
        choices = [x[1] for x in TEMPLATE_CHOICES]
        if value not in choices:
            return serializers.ValidationError(f"The valid category choices are {TEMPLATE_CHOICES}")
        return value


class SceneUpdateSerializer(serializers.Serializer):
    text = serializers.CharField(required = True, max_length = 2000)
