from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from .utils.file_utils import stored_file_exists

from .models import (
    TemplatePrompt,
    Music,
    Scene,
    SceneImage,
    VoiceModel,
    Avatar,
    UserPrompt,
    Video,
    Intro,
    Outro,
)


class TemplatePromptsSerializer(serializers.ModelSerializer):
    created_by = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = TemplatePrompt
        fields = "__all__"
        validators = [
            UniqueTogetherValidator(
                queryset=TemplatePrompt.objects.all(),
                fields=["created_by", "title"],
                message="You already have a template with this name.",
            )
        ]


class MusicSerializer(serializers.ModelSerializer):
    created_by = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Music
        fields = "__all__"


class SceneImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SceneImage
        exclude = ("scene",)


class SceneSerializer(serializers.ModelSerializer):
    scene_image = serializers.SerializerMethodField()
    narration_status = serializers.SerializerMethodField()

    def get_narration_status(self, obj):
        video = obj.video
        if not (video.settings or {}).get("narration", True):
            return "disabled"
        return "available" if stored_file_exists(obj.file) else "missing"

    class Meta:
        model = Scene
        fields = "__all__"

    def get_scene_image(self, obj):
        image = next(iter(obj.scene_images.all()), None)

        return SceneImageSerializer(image).data if image else ""


class VoiceModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = VoiceModel
        fields = ("id", "created_by", "name", "provider", "type", "sample", "path")
        read_only_fields = fields


class AvatarNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Avatar
        fields = "__all__"


class AvatarSerializer(serializers.ModelSerializer):
    sample = serializers.SerializerMethodField()
    created_by = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Avatar
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        self.fields["voice"].queryset = (
            VoiceModel.available_to(request.user) if request else VoiceModel.objects.none()
        )

    def get_sample(self, obj):
        return obj.voice.sample if obj.voice else ""


class UserPromptSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPrompt
        fields = "__all__"


VIDEO_RESPONSE_FIELDS = (
    "id", "created_by", "title", "url", "gpt_answer", "prompt", "genre", "output",
    "dir_name", "voice_model", "avatar", "status", "updated_at", "music",
    "background", "intro", "outro", "video_type", "mode", "settings",
)


class VideoSerializer(serializers.ModelSerializer):
    prompt = UserPromptSerializer(read_only=True)
    music = serializers.SerializerMethodField()

    class Meta:
        model = Video
        fields = VIDEO_RESPONSE_FIELDS
        read_only_fields = fields

    def get_music(self, obj):
        if obj.music:
            return obj.music.name

        return ""


class VideoNestedSerializer(serializers.ModelSerializer):
    prompt = UserPromptSerializer(read_only=True)
    scenes = serializers.SerializerMethodField()

    class Meta:
        model = Video
        fields = (*VIDEO_RESPONSE_FIELDS, "scenes")
        read_only_fields = fields

    def get_scenes(self, obj):
        scenes = obj.scenes.all()
        return SceneSerializer(scenes, many=True).data


class IntroSerializer(serializers.ModelSerializer):
    created_by = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Intro
        fields = "__all__"


class OutroSerializer(serializers.ModelSerializer):
    created_by = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Outro
        fields = "__all__"
