from rest_framework import serializers

from apps.videomanagement.serializers.fields import StrictCharField


class StoryDraftResultSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=50)
    story = serializers.CharField(max_length=2000)


class SceneDraftResultSerializer(serializers.Serializer):
    text = StrictCharField(max_length=320)
    image_description = StrictCharField(max_length=600)


class DraftJobSerializer(serializers.Serializer):
    id = serializers.CharField()
    status = serializers.ChoiceField(choices=["QUEUED"])
