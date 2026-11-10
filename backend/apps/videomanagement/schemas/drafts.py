from rest_framework import serializers

from apps.videomanagement.serializers.diagrams import DiagramSerializer


class StoryDraftResultSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=50)
    story = serializers.CharField(max_length=2000)


class SceneDraftResultSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=320)
    image_description = serializers.CharField(max_length=2000, allow_blank=True, default="")
    diagram = DiagramSerializer(required=False, allow_null=True)

    def validate(self, attrs):
        if not attrs.get("diagram") and not attrs["image_description"]:
            raise serializers.ValidationError("Provide a visual description or a diagram.")
        return attrs


class DraftJobSerializer(serializers.Serializer):
    id = serializers.CharField()
    status = serializers.ChoiceField(choices=["QUEUED"])
