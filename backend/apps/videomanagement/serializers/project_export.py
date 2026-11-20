import json

from rest_framework import serializers

from apps.videomanagement.models import Scene, Video
from apps.videomanagement.schemas.shot_planning import ShotPlanSerializer

from .audio import MusicAudioSerializer, SceneAudioSerializer
from .overlays import OverlaySerializer
from .requests import StoryboardSerializer, VideoUpdateSerializer


class ProjectExportOptionsSerializer(serializers.Serializer):
    include_output = serializers.BooleanField(default=False)
    check_only = serializers.BooleanField(default=False)


class ProjectSceneAudioSerializer(SceneAudioSerializer):
    duration = serializers.FloatField(required=False, allow_null=True)


class ProjectSceneSerializer(serializers.ModelSerializer):
    shot_plan = ShotPlanSerializer()
    audio_settings = ProjectSceneAudioSerializer()
    overlays = OverlaySerializer(many=True)

    class Meta:
        model = Scene
        fields = (
            "id",
            "position",
            "text",
            "script_index",
            "shot_plan",
            "caption_alignment",
            "audio_settings",
            "motion_style",
            "animation_preset",
            "animation_accents",
            "motion_intensity",
            "pause_after",
            "cuts",
            "transition_after",
            "transition_duration",
            "overlays",
        )


class ProjectVideoSerializer(serializers.ModelSerializer):
    settings = serializers.SerializerMethodField()
    storyboard = serializers.SerializerMethodField()
    prompt = serializers.CharField(source="prompt.prompt")
    voice = serializers.SerializerMethodField()

    class Meta:
        model = Video
        fields = (
            "title",
            "description",
            "tags",
            "notes",
            "genre",
            "video_type",
            "mode",
            "settings",
            "prompt",
            "storyboard",
            "voice",
            "cuts",
            "cover_settings",
            "source_audio_duration",
            "source_audio_words",
        )

    def get_settings(self, video):
        settings = video.settings or {}
        editable = dict(VideoUpdateSerializer(settings).data)
        editable.update(MusicAudioSerializer(settings).data)
        for key in (
            "gpt_model",
            "image_model",
            "provider",
            "style",
            "target_audience",
            "narration_language",
            "ai_scene_editing",
            "export_preset",
            "export_fps",
        ):
            if key in settings:
                editable[key] = settings[key]
        return editable

    def get_storyboard(self, video):
        data = video.gpt_answer
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except ValueError:
                return None
        if isinstance(data, dict) and "title" in data and "scenes" in data:
            return StoryboardSerializer(data).data
        return None

    def get_voice(self, video):
        if not video.voice_model:
            return None
        return {
            "name": video.voice_model.name,
            "provider": video.voice_model.provider,
            "type": video.voice_model.type,
        }
