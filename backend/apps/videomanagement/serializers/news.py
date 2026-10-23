from rest_framework import serializers

from apps.videomanagement.models import NewsUpdate


class NewsUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsUpdate
        fields = ["id", "title", "content", "published_at"]
        read_only_fields = fields
