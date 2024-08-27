from rest_framework import serializers

accepted_models = ["gpt-3.5-turbo", "gpt-4", "gpt-4o", "claude-3-5-sonnet-20240620",
                   "gemini-1.5-pro", "gemini-1.5-flash", "gemini-1.0-pro"]


class GenerateSerializer(serializers.Serializer):
    message = serializers.CharField(required = True, max_length = 2000)
    template_id = serializers.CharField(required = False, max_length = 20, default = "")
    voice_id = serializers.CharField(required = False, max_length = 20, default=None)
    gpt_model = serializers.ChoiceField(required = False, choices = accepted_models, default = "gpt-4o")
    images = serializers.ChoiceField(required = False, choices = ["AI", "WEB", False], default = "WEB")
    avatar_selection = serializers.CharField(required = False, max_length = 30, default = "no_avatar")
    style = serializers.ChoiceField(required = False, choices = ["vivid", "natural"], default = "vivid")
    music = serializers.CharField(required = False, max_length = 500)
    target_audience = serializers.CharField(required = False, max_length = 30, min_length = 0, default = "")
    background = serializers.CharField(required = False, max_length = 10, default = None)
    intro = serializers.CharField(required = False, max_length = 10, default = None)
    outro = serializers.CharField(required = False, max_length = 10, default = None)
    subtitles = serializers.BooleanField(required = False, default = False)
    provider = serializers.CharField(required = False, default = None)
    created_by = serializers.IntegerField(write_only = True, default = None)
    avatar_position = serializers.CharField(required = False, default = "right,top")
    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class DownloadPlaylistSerializer(serializers.Serializer):

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass

    link = serializers.URLField(required = True)
    category = serializers.ChoiceField(choices = ["Educational", "Gaming", "Advertisement", "Story", "Other"])


class SceneUpdateSerializer(serializers.Serializer):
    text = serializers.CharField(required = True, max_length = 2000)

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass


class TwitchSerializer(serializers.Serializer):
    mode = serializers.ChoiceField(choices = ["streamer", "game"], default="streamer")
    value = serializers.CharField(max_length = 200)
    amt = serializers.IntegerField(max_value = 20)
    started_at = serializers.DateField(format="%Y-%m-%d", required = False, allow_null = True)
    created_by = serializers.IntegerField(write_only = True, default = None)


    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass
