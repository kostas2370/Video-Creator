from . models import *
from rest_framework import serializers


class TemplatePromptsSerializer(serializers.ModelSerializer):

    class Meta:
        model = TemplatePrompts
        fields = "__all__"


class MusicSerializer(serializers.ModelSerializer):

    class Meta:
        model = Music
        fields = "__all__"


class SceneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scene
        fields = "__all__"





class VoiceModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = VoiceModels
        fields = "__all__"


class AvatarNestedSerializer(serializers.ModelSerializer):

    class Meta:
        model = Avatars
        fields = "__all__"

class AvatarSerializer(serializers.ModelSerializer):


    class Meta:
        model = Avatars
        fields = "__all__"

class UserpromptSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserPrompt
        fields = "__all__"


class VideoSerializer(serializers.ModelSerializer):
    prompt = UserpromptSerializer()

    class Meta:
        model = Videos
        fields = "__all__"


class VideoNestedSerializer(serializers.ModelSerializer):
    prompt = UserpromptSerializer()
    scenes = serializers.SerializerMethodField()
    class Meta:
        model = Videos
        fields = "__all__"

    def get_scenes(self, obj):
        scenes = Scene.objects.filter(prompt__video_prompt__id = obj.id)
        return SceneSerializer(scenes, many = True).data

