from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.videomanagement.services.media.uploads import inspect_media_upload

from ..models import MediaAsset
from .audio import FiniteFloat


class MediaAssetSerializer(serializers.ModelSerializer):
    # Uploads submit tags as JSON within a multipart form.
    tags = serializers.JSONField(required=False)

    class Meta:
        model = MediaAsset
        fields = (
            "id",
            "title",
            "file",
            "kind",
            "tags",
            "duration",
            "created_at",
            "source_video",
        )
        read_only_fields = ("id", "kind", "duration", "created_at", "source_video")

    def create(self, validated_data):
        if validated_data["kind"] == MediaAsset.Kind.AUDIO:
            return super().create(validated_data)
        return MediaAsset.from_visual(
            user=validated_data["created_by"],
            upload=validated_data["file"],
            title=validated_data["title"],
            tags=validated_data.get("tags", []),
            kind=validated_data["kind"],
            duration=validated_data.get("duration"),
        )

    def validate_tags(self, value):
        if not isinstance(value, list) or any(
            not isinstance(tag, str) for tag in value
        ):
            raise ValidationError("Use a list of text tags.")
        tags = serializers.ListField(
            child=serializers.CharField(min_length=1, max_length=30),
            max_length=12,
        ).run_validation([tag.strip().lower() for tag in value])
        return list(dict.fromkeys(tags))

    def validate(self, attrs):
        upload = attrs.get("file")
        if upload is None:
            return attrs
        if self.instance is not None:
            raise ValidationError(
                {"file": "Upload a new library item to use a different file."}
            )
        try:
            attrs.update(
                inspect_media_upload(
                    upload, allow_audio=True, max_image_pixels=16_000_000
                )
            )
        except ValidationError as exc:
            raise ValidationError({"file": exc.detail}) from exc
        return attrs


class UseMediaSerializer(serializers.Serializer):
    video_id = serializers.UUIDField()
    purpose = serializers.ChoiceField(choices=("new_scene", "visual", "music", "cover"))
    scene_id = serializers.UUIDField(required=False)
    text = serializers.CharField(
        required=False, allow_blank=True, max_length=2000, default=""
    )
    duration = FiniteFloat(required=False, min_value=0.1, max_value=900)
    position = serializers.IntegerField(required=False, min_value=1)
    with_audio = serializers.BooleanField(default=False)
