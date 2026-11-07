from django.conf import settings
from rest_framework import serializers


class CreativePreferencesSerializer(serializers.Serializer):
    target_audience = serializers.CharField(
        max_length=100, allow_blank=True, default=""
    )
    genre = serializers.CharField(max_length=100, allow_blank=True, default="")
    visual_style = serializers.CharField(max_length=800, allow_blank=True, default="")
    story_format = serializers.ChoiceField(
        choices=["GENERAL", "ANIMATED_STORY", "SERIAL_DRAMA"], default="GENERAL"
    )
    gpt_model = serializers.ChoiceField(
        choices=settings.ACCEPTED_MODELS, allow_blank=True, default=""
    )


class IdeaRequestSerializer(CreativePreferencesSerializer):
    kind = serializers.ChoiceField(choices=["video", "series"])
    seed = serializers.CharField(max_length=2000, allow_blank=True, default="")


class PromptRewriteRequestSerializer(CreativePreferencesSerializer):
    kind = serializers.ChoiceField(choices=["video", "series", "visual"])
    prompt = serializers.CharField(max_length=2000)
    instructions = serializers.CharField(max_length=500, allow_blank=True, default="")


class PromptResultSerializer(serializers.Serializer):
    prompt = serializers.CharField(max_length=2000)

    def to_internal_value(self, data):
        if isinstance(data, dict):
            for field in self.fields:
                if field in data and not isinstance(data[field], str):
                    raise serializers.ValidationError({field: "Expected a string."})
        return super().to_internal_value(data)


class IdeaSerializer(PromptResultSerializer):
    title = serializers.CharField(max_length=100)


class IdeaResultSerializer(serializers.Serializer):
    ideas = IdeaSerializer(many=True, min_length=3, max_length=3)

    def validate_ideas(self, ideas):
        if len({idea["title"].casefold() for idea in ideas}) != len(ideas):
            raise serializers.ValidationError("Return three distinct ideas.")
        return ideas
