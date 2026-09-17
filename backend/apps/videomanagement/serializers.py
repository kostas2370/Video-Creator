from rest_framework import serializers

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
    class Meta:
        model = TemplatePrompt
        fields = "__all__"


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
        img = SceneImage.objects.filter(scene_id=obj.id)
        if img.count() == 0:
            return ""

        return SceneImageSerializer(img.first()).data


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
        return obj.voice.sample


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
