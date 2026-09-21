from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

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

    class Meta:
        model = Scene
        fields = "__all__"

    def get_scene_image(self, obj):
        image = next(iter(obj.scene_images.all()), None)

        return SceneImageSerializer(image).data if image else ""


class VoiceModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = VoiceModel
        fields = "__all__"


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

    def get_sample(self, obj):
        return obj.voice.sample if obj.voice else ""


class UserPromptSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPrompt
        fields = "__all__"


class VideoSerializer(serializers.ModelSerializer):
    prompt = UserPromptSerializer()
    music = serializers.SerializerMethodField()

    class Meta:
        model = Video
        fields = "__all__"

    def get_music(self, obj):
        if obj.music:
            return obj.music.name

        return ""


class VideoNestedSerializer(serializers.ModelSerializer):
    prompt = UserPromptSerializer()
    scenes = serializers.SerializerMethodField()

    class Meta:
        model = Video
        fields = "__all__"

    def get_scenes(self, obj):
        scenes = obj.prompt.scenes.all()
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
