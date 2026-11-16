from rest_framework import serializers

from ..services.videos.export_freshness import export_freshness


class ExportFreshnessSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=("none", "unknown", "current", "stale"), read_only=True
    )
    exported_at = serializers.DateTimeField(allow_null=True, read_only=True)

    def to_representation(self, instance):
        return super().to_representation(export_freshness(instance))
