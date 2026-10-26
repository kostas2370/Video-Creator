from rest_framework import serializers


class StoryDraftResultSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=50)
    story = serializers.CharField(max_length=2000)


class SceneDraftResultSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=2000)
    image_description = serializers.CharField(max_length=2000)

    def to_internal_value(self, data):
        if isinstance(data, dict):
            for field in self.fields:
                if field in data and not isinstance(data[field], str):
                    raise serializers.ValidationError({field: "Expected a string."})
        return super().to_internal_value(data)
