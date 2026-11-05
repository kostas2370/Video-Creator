"""Reusable educational diagrams; no external media generation is required."""

from rest_framework import serializers

from apps.videomanagement.utils.diagrams import TEMPLATES, graph_connections, graph_levels
from apps.videomanagement.services.media.icons import available_icon_files

class DiagramItemSerializer(serializers.Serializer):
    icon = serializers.CharField(max_length=120, required=False, allow_blank=True)
    label = serializers.CharField(max_length=40)
    detail = serializers.CharField(max_length=90, allow_blank=True, default="")

    def validate_icon(self, value):
        if not value:
            return ""
        known = self.context.setdefault("diagram_icon_ids", {})
        if value not in known:
            user = self.context.get("user") or getattr(self.context.get("request"), "user", None)
            known[value] = value in available_icon_files([value], user=user)
        return value if known[value] else ""


class DiagramConnectionSerializer(serializers.Serializer):
    source = serializers.IntegerField(min_value=0, max_value=5)
    target = serializers.IntegerField(min_value=0, max_value=5)
    label = serializers.CharField(max_length=30, allow_blank=True, default="")


class DiagramSerializer(serializers.Serializer):
    template = serializers.ChoiceField(choices=tuple(TEMPLATES))
    title = serializers.CharField(max_length=60, allow_blank=True, default="")
    items = DiagramItemSerializer(many=True, min_length=2, max_length=6)
    connections = DiagramConnectionSerializer(many=True, max_length=8, required=False)

    def validate(self, attrs):
        if attrs["template"] == "comparison" and len(attrs["items"]) != 2:
            raise serializers.ValidationError("A comparison needs exactly two items.")
        maximum = TEMPLATES[attrs["template"]]["max_items"]
        if len(attrs["items"]) > maximum:
            raise serializers.ValidationError(f"This animation supports at most {maximum} items.")
        if attrs["template"] == "graph":
            connections = graph_connections(attrs)
            pairs = {(edge["source"], edge["target"]) for edge in connections}
            if len(pairs) != len(connections):
                raise serializers.ValidationError("Duplicate connections are not needed.")
            try:
                graph_levels(len(attrs["items"]), connections)
            except ValueError as exc:
                raise serializers.ValidationError(str(exc)) from exc
        elif attrs.get("connections"):
            raise serializers.ValidationError("Custom connections are available in icon graphs.")
        return attrs
