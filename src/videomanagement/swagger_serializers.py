from rest_framework import serializers

class GenerateSerializer(serializers.Serializer):
    message = serializers.CharField(required = True, max_length = 2000)
    template_id = serializers.CharField(required = False, max_length = 20)
    voice_id = serializers.CharField(required = False, max_length = 20)
    gpt_model = serializers.ChoiceField(required = False, choices = ["gpt-3.5-turbo", "gpt-4"], default = "gpt-4")
    images = serializers.ChoiceField(required = False, choices = ["DALL-E", "WEB", False], default = "WEB")
    avatar_selection = serializers.CharField(required = False, max_length = 30)
    style = serializers.ChoiceField(required = False, choices = ["vivid", "natural"], default = "vivid")
    music = serializers.CharField(required = False, max_length = 500)
    target_audience = serializers.CharField(required = False, max_length = 30, min_length = 0)


class DownloadPlaylistSerializer(serializers.Serializer):

    link = serializers.URLField(required = True)
    category = serializers.ChoiceField(choices = ["Educational", "Gaming", "Advertisement", "Story", "Other"])


class SceneUpdateSerializer(serializers.Serializer):
    text = serializers.CharField(required = True, max_length = 2000)


class TwitchSerializer(serializers.Serializer):
    mode = serializers.ChoiceField(choices = ["Streamer", "Game"] , default="Streamer")
    value = serializers.CharField(max_length = 200)
    amt = serializers.IntegerField(max_value = 20)
