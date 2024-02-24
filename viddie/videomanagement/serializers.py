"""
Viddie is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as
published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

Viddie is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.
"""


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

        img = SceneImage.objects.filter(scene_id = obj.id)
        if img.count() == 0:
            return ""

        return SceneImageSerializer(img.first()).data


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


