from uuid import UUID

from django.db import transaction
from rest_framework import serializers

from apps.series.creative import series_visual_continuity
from apps.series.models import (
    CHARACTER_PROFILE_FIELDS,
    CHARACTER_REFERENCE_FIELDS,
    Character,
    SeriesEpisode,
    VideoSeries,
)
from apps.series.services.characters import (
    cast_is_ready,
    replace_series_cast,
    validated_cast_references,
)
from apps.videomanagement.integrations.visuals import ImageProviderRegistry
from apps.videomanagement.models import Intro, Outro
from apps.videomanagement.serializers.fields import (
    validate_image_upload,
    validate_reference_image,
)
from apps.videomanagement.serializers.requests import GenerateSerializer
from apps.videomanagement.services.media.selection import available_voice, owned_asset


class CharacterImagePathField(serializers.CharField):
    def to_representation(self, value):
        return value.url if value else None


class CharacterSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField()
    image = CharacterImagePathField(required=False, allow_blank=True, allow_null=True)
    pending_image = CharacterImagePathField(read_only=True)

    class Meta:
        model = Character
        fields = (
            "id",
            *CHARACTER_PROFILE_FIELDS,
            "visual_style",
            "image",
            "pending_image",
            "image_approved",
            "status",
            "error",
        )
        read_only_fields = ("status", "error")


def serialize_cast(series):
    return CharacterSerializer(series.cast_members.all(), many=True).data


class CastField(serializers.JSONField):
    def to_representation(self, value):
        return CharacterSerializer(value.all(), many=True).data


class CastDraftRequestSerializer(serializers.Serializer):
    premise = serializers.CharField(max_length=2000)
    visual_style = serializers.CharField(max_length=800)
    story_format = serializers.ChoiceField(
        choices=VideoSeries._meta.get_field("story_format").choices
    )
    count = serializers.IntegerField(min_value=1, max_value=6, default=2)


class CharacterDescriptionRequestSerializer(CastDraftRequestSerializer):
    count = serializers.IntegerField(min_value=1, max_value=1, default=1)
    name = serializers.CharField(max_length=60, allow_blank=True, default="")
    idea = serializers.CharField(max_length=500, allow_blank=True, default="")
    appearance = serializers.CharField(max_length=300, allow_blank=True, default="")
    wardrobe = serializers.CharField(max_length=150, allow_blank=True, default="")
    personality = serializers.CharField(max_length=200, allow_blank=True, default="")
    relationships = serializers.CharField(max_length=200, allow_blank=True, default="")
    cast_names = serializers.ListField(
        child=serializers.CharField(max_length=60), max_length=6, required=False
    )


class CharacterImageQuerySerializer(serializers.Serializer):
    id = serializers.UUIDField()


class CharacterImageRequestSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(required=False)

    class Meta:
        model = Character
        fields = ("id", *CHARACTER_REFERENCE_FIELDS, "image")
        extra_kwargs = {
            "visual_style": {"required": True, "allow_blank": False},
        }

    def validate_image(self, value):
        return validate_image_upload(
            value,
            max_pixels=25000000,
            still_only=True,
            messages={
                "size": "Choose an image smaller than 10 MB.",
                "format": "Choose a PNG, JPEG or WebP image.",
                "pixels": "Choose an image with at most 25 million pixels.",
                "animated": "Choose a still image.",
            },
        )


class VideoSeriesSerializer(serializers.ModelSerializer):
    # Parse JSON/multipart input; the database stores related Character rows.
    cast = CastField(source="cast_members", required=False)
    cast_ready = serializers.SerializerMethodField()
    episode_count = serializers.IntegerField(read_only=True)
    active_episode = serializers.SerializerMethodField()

    @transaction.atomic
    def create(self, validated_data):
        cast = validated_data.pop("cast_members", [])
        series = super().create(validated_data)
        replace_series_cast(series, cast)
        return series

    @transaction.atomic
    def update(self, instance, validated_data):
        instance = VideoSeries.objects.select_for_update().get(pk=instance.pk)
        cast = validated_data.pop("cast_members", None)
        series = super().update(instance, validated_data)
        if cast is not None:
            replace_series_cast(series, cast)
        return series

    def get_cast_ready(self, series):
        return cast_is_ready(
            series.cast_members.all(), series.story_format, series.visual_style
        )

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
            "cast",
            "cast_ready",
            "story_format",
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

    def validate_cast(self, value):
        serializer = CharacterSerializer(data=value, many=True, max_length=6)
        serializer.is_valid(raise_exception=True)
        cast = [
            dict(character, id=str(character["id"]))
            for character in serializer.validated_data
        ]
        if len({character["id"] for character in cast}) != len(cast):
            raise serializers.ValidationError("Each character must have a unique ID.")
        if len({character["name"].casefold() for character in cast}) != len(cast):
            raise serializers.ValidationError("Give each character a different name.")
        return cast

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

        if "cast_members" in attrs:
            cast = attrs["cast_members"]
        elif self.instance:
            cast = serialize_cast(self.instance)
        else:
            cast = []
        continuity = series_visual_continuity(
            characters=current("characters", ""),
            visual_style=current("visual_style", ""),
            cast=cast,
        )
        if len(continuity) > 3000:
            raise serializers.ValidationError(
                {
                    "characters": "Shorten the cast appearance, wardrobe, world or style descriptions; combined visual guidance must fit within 3,000 characters."
                }
            )
        if current("narration", True) and not current("voice_model_id"):
            raise serializers.ValidationError(
                {
                    "voice_model": "Choose a narrator to keep the same voice across episodes, or turn narration off."
                }
            )
        provider = current("provider", "OPENAI")
        if any(
            character.get("image") for character in cast
        ) and not ImageProviderRegistry.supports_reference(provider):
            raise serializers.ValidationError(
                {
                    "provider": "Choose a visual provider with reference-image support to use your character images."
                }
            )
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
        validated_cast_references(series)
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
            "visual_continuity": series_visual_continuity(
                characters=series.characters,
                visual_style=series.visual_style,
                cast=serialize_cast(series),
            ),
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
