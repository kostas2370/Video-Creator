from rest_framework import serializers

from .requests import StoryboardSerializer


class StoryboardRevisionSerializer(serializers.Serializer):
    instructions = serializers.CharField(max_length=2000)
    storyboard = StoryboardSerializer()
