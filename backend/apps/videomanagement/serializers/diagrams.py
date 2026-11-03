"""Reusable educational diagrams; no external media generation is required."""

from rest_framework import serializers

from apps.videomanagement.utils.diagrams import TEMPLATES

class DiagramItemSerializer(serializers.Serializer):
    label = serializers.CharField(max_length=40)
    detail = serializers.CharField(max_length=90, allow_blank=True, default="")


class DiagramSerializer(serializers.Serializer):
    template = serializers.ChoiceField(choices=tuple(TEMPLATES))
    title = serializers.CharField(max_length=60, allow_blank=True, default="")
    items = DiagramItemSerializer(many=True, min_length=2, max_length=4)

    def validate(self, attrs):
        if attrs["template"] == "comparison" and len(attrs["items"]) != 2:
            raise serializers.ValidationError("A comparison needs exactly two items.")
        return attrs
