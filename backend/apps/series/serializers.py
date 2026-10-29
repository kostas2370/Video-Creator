from uuid import UUID

from rest_framework import serializers

from apps.series.models import SeriesEpisode, VideoSeries
from apps.videomanagement.integrations.visuals import ImageProviderRegistry
from apps.videomanagement.models import Intro, Outro
from apps.videomanagement.serializers.fields import validate_reference_image
from apps.videomanagement.serializers.requests import GenerateSerializer
from apps.videomanagement.services.media.selection import available_voice, owned_asset


class VideoSeriesSerializer(serializers.ModelSerializer):
    episode_count = serializers.IntegerField(read_only=True)
    active_episode = serializers.SerializerMethodField()

    def get_active_episode(self, series):
        if not getattr(series, "active_episode_id", None):
            return None
        return {
            "id": str(UUID(str(series.active_episode_id))),
            "video_id": str(UUID(str(series.active_video_id))),
            "number": series.active_episode_number,
        }

    voice_model = serializers.UUIDField(
        source="voice_model_id", required=False, allow_null=True
    )
    intro = serializers.UUIDField(source="intro_id", required=False, allow_null=True)
    outro = serializers.UUIDField(source="outro_id", required=False, allow_null=True)
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
            "active_episode",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_reference_image(self, value):
        return validate_reference_image(value)

    def validate_intro(self, value):
        selected = owned_asset(Intro, value, self.context["request"].user)
        return selected.pk if selected else None

    def validate_outro(self, value):
        selected = owned_asset(Outro, value, self.context["request"].user)
        return selected.pk if selected else None

    def validate_voice_model(self, value):
        selected = available_voice(value, self.context["request"].user)
        return selected.pk if selected else None

    def validate(self, attrs):
        def current(field, default=None):
            return attrs.get(field, getattr(self.instance, field, default))

        if current("narration", True) and not current("voice_model_id"):
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


def validate_episode_generation(choices, context):
    # Snapshot defaults in one place, using the same validation as standalone AI videos.
    data = {key: value for key, value in choices.items() if value is not None}
    # Generation fields expect strings; saved profiles may contain UUID objects.
    for field in ("voice_id", "intro", "outro"):
        if field in data:
            data[field] = str(data[field])
    serializer = GenerateSerializer(
        data=data,
        context=context,
    )
    serializer.is_valid(raise_exception=True)
    params = dict(serializer.validated_data)
    params.pop("created_by")
    return params


class EpisodeDraftSerializer(serializers.Serializer):
    idea = serializers.CharField(max_length=2000)

    def validate(self, attrs):
        series = self.context["series"]
        if series.narration and not series.voice_model_id:
            raise serializers.ValidationError(
                {
                    "voice_model": "Choose a narrator in the series setup before drafting."
                }
            )
        choices = {
            "message": attrs["idea"],
            "image_mode": "AI",
            "provider": series.provider,
            "voice_id": series.voice_model_id,
            "intro": series.intro_id,
            "outro": series.outro_id,
            "narration": series.narration,
            "subtitles": series.subtitles,
            "video_format": series.video_format,
            "platform": series.platform,
            "scene_count": series.scene_count,
            "review_script": True,
            "visual_continuity": f"Cast: {series.characters}\nStyle: {series.visual_style}",
        }
        attrs["generation_params"] = validate_episode_generation(choices, self.context)
        return attrs


class EpisodeMemoryDraftSerializer(serializers.Serializer):
    summary = serializers.CharField(max_length=800, allow_blank=True, required=False)


class EpisodeMemorySerializer(serializers.Serializer):
    script_hash = serializers.RegexField(
        r"\A[0-9a-f]{64}\Z", allow_blank=True, trim_whitespace=False
    )
    previous_summary = serializers.CharField(
        max_length=800, allow_blank=True, trim_whitespace=False
    )
    summary = serializers.CharField(max_length=800, allow_blank=True)


class SeriesEpisodeSerializer(serializers.ModelSerializer):
    video_id = serializers.UUIDField(read_only=True)
    video_title = serializers.CharField(
        source="video.title", read_only=True, default=None
    )
    status = serializers.CharField(source="video.status", read_only=True, default=None)
    can_retry = serializers.BooleanField(read_only=True)
    script_hash = serializers.CharField(read_only=True)
    memory_needs_review = serializers.BooleanField(read_only=True)
    can_update_memory = serializers.BooleanField(read_only=True)

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
            "script_hash",
            "memory_needs_review",
            "can_update_memory",
            "is_canon",
            "created_at",
        )
        read_only_fields = fields
