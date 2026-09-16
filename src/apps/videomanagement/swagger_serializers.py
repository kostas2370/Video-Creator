from django.conf import settings
from rest_framework import serializers

DEFAULT_GPT_MODEL = settings.DEFAULT_GPT_MODEL

# Chat Completions models only — that is what gpt_utils calls. The `-pro` and `-codex`
# variants are served through the Responses API and would only 400 here.
accepted_models = [
    # OpenAI — legacy, kept so existing callers do not break.
    "gpt-3.5-turbo",
    "gpt-4",
    "gpt-4-turbo",
    "gpt-4o",
    "gpt-4o-mini",
    # OpenAI — 4.1 family.
    "gpt-4.1",
    "gpt-4.1-mini",
    "gpt-4.1-nano",
    # OpenAI — 5 family and later.
    "gpt-5",
    "gpt-5-mini",
    "gpt-5-nano",
    "gpt-5-chat-latest",
    "gpt-5.1",
    "gpt-5.1-chat-latest",
    "gpt-5.2",
    "gpt-5.2-chat-latest",
    "gpt-5.3-chat-latest",
    "gpt-5.4",
    "gpt-5.4-mini",
    "gpt-5.4-nano",
    "gpt-5.5",
    "gpt-5.6-luna",
    "gpt-5.6-sol",
    "gpt-5.6-terra",
    "gpt-6-astra",
    # OpenAI — o-series reasoning models.
    "o1",
    "o3",
    "o3-mini",
    "o4-mini",
    "claude-3-5-sonnet-20240620",
    "gemini-1.5-pro",
    "gemini-1.5-flash",
    "gemini-1.0-pro",
]

# Otherwise a custom DEFAULT_GPT_MODEL would be advertised as the default yet rejected.
if DEFAULT_GPT_MODEL not in accepted_models:
    accepted_models.append(DEFAULT_GPT_MODEL)


class GenerateSerializer(serializers.Serializer):
    message = serializers.CharField(required=True, max_length=2000)
    template_id = serializers.CharField(required=False, max_length=20, default="")
    voice_id = serializers.CharField(required=False, max_length=20, default=None)
    gpt_model = serializers.ChoiceField(
        required=False, choices=accepted_models, default=DEFAULT_GPT_MODEL
    )
    image_mode = serializers.ChoiceField(
        required=False, choices=["AI", "WEB", False], default="WEB"
    )
    avatar_selection = serializers.CharField(required=False, max_length=30, default="")
    style = serializers.ChoiceField(
        required=False, choices=["vivid", "natural"], default="vivid"
    )
    music = serializers.CharField(required=False, max_length=500)
    target_audience = serializers.CharField(
        required=False, max_length=30, min_length=0, default=""
    )
    background = serializers.CharField(required=False, max_length=10, default=None)
    intro = serializers.CharField(required=False, max_length=10, default=None)
    outro = serializers.CharField(required=False, max_length=10, default=None)
    subtitles = serializers.BooleanField(required=False, default=False)
    provider = serializers.CharField(required=False, default=None)
    # HiddenField, not IntegerField: the default is a User object, so a client that
    # posted `created_by` used to both break the service and attribute the video (and
    # its cost) to another account. A HiddenField is never read from the payload.
    created_by = serializers.HiddenField(default=serializers.CurrentUserDefault())
    avatar_position = serializers.CharField(required=False, default="right,top")

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class DownloadPlaylistSerializer(serializers.Serializer):
    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass

    link = serializers.URLField(required=True)
    category = serializers.ChoiceField(
        choices=["Educational", "Gaming", "Advertisement", "Story", "Other"]
    )


class SceneUpdateSerializer(serializers.Serializer):
    text = serializers.CharField(required=True, max_length=2000)

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass


class TwitchSerializer(serializers.Serializer):
    mode = serializers.ChoiceField(choices=["streamer", "game"], default="streamer")
    value = serializers.CharField(max_length=200)
    amt = serializers.IntegerField(max_value=20)
    started_at = serializers.DateField(
        format="%Y-%m-%d", required=False, allow_null=True, default=None
    )
    created_by = serializers.HiddenField(default=serializers.CurrentUserDefault())

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass


class VideoUpdateSerializer(serializers.Serializer):
    avatar = serializers.CharField(required=False, default=None, allow_null=True)
    intro = serializers.CharField(required=False, default=None, allow_null=True)
    outro = serializers.CharField(required=False, default=None, allow_null=True)
    title = serializers.CharField(required=False, default=None)
    subtitles = serializers.BooleanField(required=False, default=None)
    avatar_position = serializers.ChoiceField(
        choices=["left,top", "right,top", "left,bottom", "right,bottom"],
        default="streamer",
        allow_null=True,
    )

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass


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

    def to_representation(self, instance):
        data = super().to_representation(instance)
        mode = data.pop("mode")

        if mode == "AI" and "url" in data:
            data.pop("url")
        elif data == "TWITCH":
            data = {"url": data["url"]}

        return data
