from django.conf import settings
from rest_framework import serializers

from .models import Avatar, Intro, Outro
from .services.asset_selection import available_voice, owned_asset


class GenerateSerializer(serializers.Serializer):
    message = serializers.CharField(required=True, max_length=2000)
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

    def validate(self, attrs):
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


class TwitchSerializer(serializers.Serializer):
    mode = serializers.ChoiceField(choices=["streamer", "game"], default="streamer")
    value = serializers.CharField(max_length=200)
    amt = serializers.IntegerField(max_value=20)
    started_at = serializers.DateField(
        format="%Y-%m-%d", required=False, allow_null=True, default=None
    )
    created_by = serializers.HiddenField(default=serializers.CurrentUserDefault())


class VideoUpdateSerializer(serializers.Serializer):
    avatar = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    intro = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    outro = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    title = serializers.CharField(required=False, max_length=50)
    subtitles = serializers.BooleanField(required=False)
    avatar_position = serializers.ChoiceField(
        choices=["left,top", "right,top", "left,bottom", "right,bottom"],
        required=False,
    )


class AddSceneSerializer(serializers.Serializer):
    mode = serializers.ChoiceField(choices=["AI", "TWITCH"])
    url = serializers.URLField(required=False)
    text = serializers.CharField(required=False)
    image_description = serializers.CharField(required=False)
    is_last = serializers.BooleanField(default=False)
    with_audio = serializers.BooleanField(default=False)

    def validate(self, attrs):
        if attrs.get("mode") == "AI":
            if not attrs.get("text"):
                raise serializers.ValidationError("text field required !")

        else:
            if not attrs.get("url"):
                raise serializers.ValidationError("url field required !")

        return super().validate(attrs)
