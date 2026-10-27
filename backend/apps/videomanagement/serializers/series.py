from rest_framework import serializers

from apps.videomanagement.integrations.visuals import ImageProviderRegistry
from apps.videomanagement.models import Intro, Outro, SeriesEpisode, VideoSeries
from apps.videomanagement.services.media.selection import available_voice, owned_asset

from .fields import validate_image_upload


class AssetUUIDField(serializers.UUIDField):
    def to_representation(self, value):
        return str(getattr(value, "pk", value))


class VideoSeriesSerializer(serializers.ModelSerializer):
    episode_count = serializers.IntegerField(read_only=True)
    voice_model = AssetUUIDField(required=False, allow_null=True)
    intro = AssetUUIDField(required=False, allow_null=True)
    outro = AssetUUIDField(required=False, allow_null=True)
    remove_reference = serializers.BooleanField(
        write_only=True, required=False, default=False
    )

    class Meta:
        model = VideoSeries
        fields = (
            "id",
            "title",
            "premise",
            "characters",
            "visual_style",
            "reference_image",
            "remove_reference",
            "voice_model",
            "intro",
            "outro",
            "provider",
            "narration",
            "subtitles",
            "video_format",
            "platform",
            "scene_count",
            "episode_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_reference_image(self, value):
        return validate_image_upload(
            value,
            check_order=("size", "format"),
            messages={
                "size": "Choose an image smaller than 10 MB.",
                "format": "Choose a PNG, JPEG, or WebP image.",
            },
        )

    def validate(self, attrs):
        owner = self.context["request"].user
        for field, model in (("intro", Intro), ("outro", Outro)):
            if field in attrs:
                attrs[field] = owned_asset(model, attrs[field], owner)
        if "voice_model" in attrs:
            attrs["voice_model"] = available_voice(attrs["voice_model"], owner)

        def current(field, default=None):
            return attrs.get(field, getattr(self.instance, field, default))

        if current("narration", True) and not current("voice_model"):
            raise serializers.ValidationError(
                {
                    "voice_model": "Choose a narrator to keep the same voice across episodes, or turn narration off."
                }
            )
        provider = current("provider", "OPENAI")
        # Start with the built-in providers whose reference handling is known.
        if ImageProviderRegistry.registration(provider, "AI") is None:
            raise serializers.ValidationError(
                {"provider": "Choose a built-in AI visual provider."}
            )
        remove = attrs.pop("remove_reference", False)
        reference = current("reference_image")
        if remove and attrs.get("reference_image"):
            raise serializers.ValidationError(
                {
                    "reference_image": "Upload a reference or remove it, rather than both."
                }
            )
        if (
            reference
            and not remove
            and not ImageProviderRegistry.supports_reference(provider)
        ):
            raise serializers.ValidationError(
                {
                    "provider": "Choose a provider that supports the series reference image, or remove the reference."
                }
            )
        if remove:
            attrs["reference_image"] = ""
        return attrs


class EpisodeDraftSerializer(serializers.Serializer):
    idea = serializers.CharField(max_length=2000)


class EpisodeMemorySerializer(serializers.Serializer):
    previous_summary = serializers.CharField(
        max_length=800, allow_blank=True, required=False, trim_whitespace=False
    )
    summary = serializers.CharField(max_length=800, allow_blank=True)


class SeriesEpisodeSerializer(serializers.ModelSerializer):
    video_id = serializers.UUIDField(read_only=True)
    video_title = serializers.CharField(
        source="video.title", read_only=True, default=None
    )
    status = serializers.CharField(source="video.status", read_only=True, default=None)
    can_retry = serializers.SerializerMethodField()

    def get_can_retry(self, episode):
        return bool(
            episode.video
            and episode.video.status == "FAILED"
            and not episode.video.gpt_answer
        )

    class Meta:
        model = SeriesEpisode
        fields = (
            "id",
            "number",
            "idea",
            "summary",
            "video_id",
            "video_title",
            "status",
            "can_retry",
            "is_canon",
            "created_at",
        )
        read_only_fields = fields
