from django.conf import settings
from rest_framework import serializers

from .models import Avatar, Intro, Outro
from .services.asset_selection import available_voice, owned_asset
from .video_formats import (
    DEFAULT_VIDEO_FORMAT,
    DEFAULT_VIDEO_PLATFORM,
    VIDEO_FORMAT_CHOICES,
    VIDEO_PLATFORM_CHOICES,
)

AVATAR_POSITIONS = {"left,top", "right,top", "left,bottom", "right,bottom"}


def normalize_avatar_position(value):
    """Return the canonical horizontal,vertical form used by video rendering."""
    parts = str(value or "").split(",")
    horizontal = next((part for part in parts if part in {"left", "right"}), None)
    vertical = next((part for part in parts if part in {"top", "bottom"}), None)
    normalized = f"{horizontal},{vertical}" if horizontal and vertical else ""
    if normalized not in AVATAR_POSITIONS:
        raise serializers.ValidationError(
            "Select a valid choice. Valid choices are: left,top, right,top, left,bottom, right,bottom."
        )
    return normalized


class GenerateSerializer(serializers.Serializer):
    scene_count = serializers.IntegerField(required=False, allow_null=True, min_value=1, max_value=60)
    reference_image = serializers.ImageField(required=False)
    message = serializers.CharField(required=True, max_length=2000)
    video_format = serializers.ChoiceField(
        required=False, choices=VIDEO_FORMAT_CHOICES, default=DEFAULT_VIDEO_FORMAT
    )
    platform = serializers.ChoiceField(
        required=False, choices=VIDEO_PLATFORM_CHOICES, default=DEFAULT_VIDEO_PLATFORM
    )
    voice_id = serializers.CharField(
        required=False, max_length=20, default=None, allow_blank=True, allow_null=True
    )
    gpt_model = serializers.ChoiceField(
        required=False,
        choices=settings.ACCEPTED_MODELS,
        default=settings.DEFAULT_GPT_MODEL,
    )
    image_mode = serializers.ChoiceField(
        required=False, choices=["AI", "WEB", False], default="WEB"
    )
    avatar_selection = serializers.CharField(
        required=False, max_length=30, default="", allow_blank=True, allow_null=True
    )
    style = serializers.ChoiceField(
        required=False, choices=["vivid", "natural"], default="vivid"
    )
    music = serializers.CharField(
        required=False, max_length=500, default="", allow_blank=True, allow_null=True
    )
    target_audience = serializers.CharField(
        required=False, max_length=30, min_length=0, default="", allow_blank=True
    )
    background = serializers.CharField(required=False, max_length=10, default=None)
    intro = serializers.CharField(required=False, max_length=10, default=None)
    outro = serializers.CharField(required=False, max_length=10, default=None)
    subtitles = serializers.BooleanField(required=False, default=False)
    narration = serializers.BooleanField(required=False, default=True)
    provider = serializers.CharField(required=False, default=None)
    created_by = serializers.HiddenField(default=serializers.CurrentUserDefault())
    avatar_position = serializers.CharField(required=False, default="right,top")
    genre = serializers.CharField(required=False, default="", allow_blank=True)

    def validate_reference_image(self, value):
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("Choose an image smaller than 10 MB.")
        if value.image.format not in {"JPEG", "PNG", "WEBP"}:
            raise serializers.ValidationError("Choose a PNG, JPEG, or WebP image.")
        return value

    def validate(self, attrs):
        if attrs.get("reference_image") and (
            attrs.get("image_mode") != "AI"
            or attrs.get("provider") not in (None, "OPENAI", "sora")
        ):
            raise serializers.ValidationError(
                {
                    "reference_image": "Reference images are supported with OpenAI images and Sora."
                }
            )
        attrs["avatar_position"] = normalize_avatar_position(
            attrs.get("avatar_position", "right,top")
        )
        for field, model in (
            ("avatar_selection", Avatar),
            ("intro", Intro),
            ("outro", Outro),
        ):
            owned_asset(model, attrs.get(field), attrs["created_by"])
        if not attrs.get("avatar_selection"):
            available_voice(attrs.get("voice_id"), attrs["created_by"])
        return attrs


class DownloadPlaylistSerializer(serializers.Serializer):
    link = serializers.URLField(required=True)
    category = serializers.ChoiceField(
        choices=["Educational", "Gaming", "Advertisement", "Story", "Other"]
    )


class SceneDraftSerializer(serializers.Serializer):
    prompt = serializers.CharField(max_length=2000)
    use_context = serializers.BooleanField(default=False)
    draft_type = serializers.ChoiceField(choices=["sentence", "section", "story"], default="sentence")
    sentence_count = serializers.IntegerField(default=1, min_value=1, max_value=12)

    def validate(self, attrs):
        if attrs["draft_type"] == "sentence" and attrs["sentence_count"] != 1:
            raise serializers.ValidationError("A sentence draft contains exactly one sentence.")
        return attrs


class SceneDraftResultSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=320)
    image_description = serializers.CharField(max_length=600)

    def to_internal_value(self, data):
        if isinstance(data, dict):
            for field in self.fields:
                if field in data and not isinstance(data[field], str):
                    raise serializers.ValidationError({field: "Expected a string."})
        return super().to_internal_value(data)


class SceneUpdateSerializer(serializers.Serializer):
    text = serializers.CharField(required=True, max_length=2000)


class ChangeSceneImageSerializer(serializers.Serializer):
    image = serializers.FileField(required=False)
    with_audio = serializers.BooleanField(default=False)

    def validate(self, attrs):
        if not self.context.get("has_scene_image") and "image" not in attrs:
            raise serializers.ValidationError({"image": "You must add an image!"})
        return attrs


class SceneImageQuerySerializer(serializers.Serializer):
    scene_image = serializers.IntegerField(min_value=1, required=False)


class GenerateSceneImageSerializer(serializers.Serializer):
    image_description = serializers.CharField(max_length=2000)


class VideoUpdateSerializer(serializers.Serializer):
    avatar = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    intro = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    outro = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    title = serializers.CharField(required=False, max_length=50)
    video_format = serializers.ChoiceField(choices=VIDEO_FORMAT_CHOICES, required=False)
    platform = serializers.ChoiceField(choices=VIDEO_PLATFORM_CHOICES, required=False)
    subtitles = serializers.BooleanField(required=False)
    avatar_position = serializers.CharField(required=False)

    def validate_avatar_position(self, value):
        return normalize_avatar_position(value)

    def update(self, instance, validated_data):
        from .services.VideoServices import video_update

        return video_update(instance, **validated_data)


class AddSceneSerializer(serializers.Serializer):
    text = serializers.CharField(required=False)
    image_description = serializers.CharField(required=False)
    is_last = serializers.BooleanField(default=False)
    with_audio = serializers.BooleanField(default=False)

    def validate(self, attrs):
        if not attrs.get("text"):
            raise serializers.ValidationError("text field required !")

        return super().validate(attrs)


class AddScenesSerializer(serializers.Serializer):
    scenes = AddSceneSerializer(many=True, min_length=1, max_length=12)
