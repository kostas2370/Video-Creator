"""Shared portable project schemas for export and validated import."""

import json

from rest_framework import serializers

from apps.videomanagement.models import MediaAsset, Scene, Video
from apps.videomanagement.schemas.shot_planning import ShotPlanSerializer

from .audio import MusicAudioSerializer, SceneAudioSerializer
from .caption_words import CaptionWordSerializer
from .covers import CoverSettingsSerializer
from .fields import FiniteFloat
from .overlays import OverlaySerializer
from .requests import (
    RenderVideoSerializer,
    SceneCutsSerializer,
    StoryboardSerializer,
    VideoUpdateSerializer,
)

MAX_PROJECT_BYTES = 1024 * 1024 * 1024
MEDIA_PATH_PATTERN = r"\Amedia/[a-zA-Z0-9_-]+\.[a-zA-Z0-9]{1,10}\Z"


class ArchiveCutsSerializer(SceneCutsSerializer):
    previous = None
    source_key = serializers.RegexField(r"\A[a-f0-9]{64}\Z", required=False)


class ProjectCutsField(serializers.JSONField):
    def to_internal_value(self, data):
        return {} if data == {} else ArchiveCutsSerializer().run_validation(data)


class ProjectSettingsSerializer(
    VideoUpdateSerializer, MusicAudioSerializer, RenderVideoSerializer
):
    voice_id = None
    narration_scenes = None
    retry_narration = None

    gpt_model = serializers.CharField(max_length=200, required=False)
    image_model = serializers.CharField(max_length=200, required=False)
    provider = serializers.CharField(max_length=100, required=False)
    style = serializers.CharField(max_length=100, required=False, allow_blank=True)
    target_audience = serializers.CharField(
        max_length=100, required=False, allow_blank=True
    )
    narration_language = serializers.CharField(
        max_length=80, required=False, allow_blank=True
    )
    ai_scene_editing = serializers.BooleanField(required=False)


class ProjectExportOptionsSerializer(serializers.Serializer):
    include_output = serializers.BooleanField(default=False)
    check_only = serializers.BooleanField(default=False)


class ProjectSceneAudioSerializer(SceneAudioSerializer):
    duration = FiniteFloat(
        min_value=0.1, max_value=900, required=False, allow_null=True
    )


class ProjectSceneSerializer(serializers.ModelSerializer):
    shot_plan = ShotPlanSerializer()
    audio_settings = ProjectSceneAudioSerializer()
    overlays = OverlaySerializer(many=True)
    cuts = ProjectCutsField()

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
    cuts = ProjectCutsField()

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
        return ProjectSettingsSerializer(video.settings or {}).data

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


class ProjectImportUploadSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, upload):
        if upload.size > MAX_PROJECT_BYTES:
            raise serializers.ValidationError("Choose a project ZIP smaller than 1 GB.")
        return upload


class ArchiveFileSerializer(serializers.Serializer):
    path = serializers.RegexField(MEDIA_PATH_PATTERN)
    size = serializers.IntegerField(min_value=0, max_value=MAX_PROJECT_BYTES)
    sha256 = serializers.RegexField(r"\A[a-f0-9]{64}\Z")


class ArchiveLicenseSerializer(serializers.Serializer):
    attribution = serializers.CharField(allow_blank=True, max_length=10000)
    license_url = serializers.URLField(allow_blank=True, max_length=500)
    source_url = serializers.URLField(allow_blank=True, max_length=500, required=False)


class ArchiveResourceSerializer(serializers.Serializer):
    id = serializers.UUIDField(required=False)
    name = serializers.CharField(max_length=100, allow_blank=True)
    file = serializers.CharField(allow_null=True)


class ArchiveMusicSerializer(ArchiveResourceSerializer):
    name = serializers.CharField(max_length=140, allow_blank=True)
    license = ArchiveLicenseSerializer(required=False)


class ArchiveAssetSerializer(serializers.Serializer):
    file = serializers.CharField(allow_null=True)
    title = serializers.CharField(max_length=100, allow_blank=True)
    kind = serializers.ChoiceField(choices=MediaAsset.Kind.choices)
    tags = serializers.ListField(
        child=serializers.CharField(max_length=200), max_length=100
    )
    duration = FiniteFloat(min_value=0, allow_null=True)


class ArchiveVisualSerializer(serializers.Serializer):
    prompt = serializers.CharField(allow_blank=True, allow_null=True, max_length=10000)
    with_audio = serializers.BooleanField()
    asset = ArchiveAssetSerializer(allow_null=True)


class ArchiveAlignmentSerializer(serializers.Serializer):
    words = CaptionWordSerializer(many=True, max_length=10000, required=False)
    source = serializers.CharField(required=False, max_length=64)


class ArchiveSceneSerializer(ProjectSceneSerializer):
    id = serializers.UUIDField()
    position = serializers.IntegerField(min_value=1, max_value=2147483647)
    script_index = serializers.IntegerField(
        min_value=0, max_value=2147483647, allow_null=True
    )
    text = serializers.CharField(allow_blank=True, max_length=100000)
    caption_alignment = ArchiveAlignmentSerializer()
    pause_after = FiniteFloat(min_value=0, max_value=10)
    transition_duration = FiniteFloat(min_value=0, max_value=10, allow_null=True)
    narration = serializers.CharField(allow_null=True)
    voiceover = serializers.CharField(allow_null=True)
    overlay_logo = serializers.CharField(allow_null=True)
    starting_asset = ArchiveAssetSerializer(allow_null=True)
    visuals = ArchiveVisualSerializer(many=True, max_length=500)

    class Meta(ProjectSceneSerializer.Meta):
        fields = (
            *ProjectSceneSerializer.Meta.fields,
            "narration",
            "voiceover",
            "overlay_logo",
            "starting_asset",
            "visuals",
        )


class ArchiveProjectSerializer(ProjectVideoSerializer):
    prompt = serializers.CharField(allow_blank=True, max_length=100000)
    settings = ProjectSettingsSerializer()
    storyboard = StoryboardSerializer(allow_null=True)
    source_audio_duration = FiniteFloat(min_value=0, allow_null=True)
    source_audio_words = CaptionWordSerializer(many=True, max_length=10000)
    cover_settings = serializers.JSONField()
    avatar = ArchiveResourceSerializer(allow_null=True)
    intro = ArchiveResourceSerializer(allow_null=True)
    outro = ArchiveResourceSerializer(allow_null=True)
    music = ArchiveMusicSerializer(allow_null=True)
    reference_image = serializers.CharField(allow_null=True)
    source_audio = serializers.CharField(allow_null=True)
    cover = serializers.CharField(allow_null=True)
    thumbnail = serializers.CharField(allow_null=True)
    output = serializers.CharField(allow_null=True)

    class Meta(ProjectVideoSerializer.Meta):
        fields = tuple(
            name for name in ProjectVideoSerializer.Meta.fields if name != "voice"
        ) + (
            "avatar",
            "intro",
            "outro",
            "music",
            "reference_image",
            "source_audio",
            "cover",
            "thumbnail",
            "output",
        )

    def validate_cover_settings(self, value):
        return CoverSettingsSerializer(partial=True).run_validation(value)


class ArchiveIconSerializer(serializers.Serializer):
    key = serializers.CharField(max_length=120)
    file = serializers.CharField()
    license = serializers.CharField(allow_blank=True, max_length=80)
    license_url = serializers.URLField(allow_blank=True, max_length=500)
    attribution = serializers.CharField(allow_blank=True, max_length=250)


class ProjectManifestSerializer(serializers.Serializer):
    format = serializers.ChoiceField(choices=("viddie-project",))
    version = serializers.IntegerField(min_value=1, max_value=1)
    project = ArchiveProjectSerializer()
    scenes = ArchiveSceneSerializer(many=True, max_length=500)
    icons = ArchiveIconSerializer(many=True, max_length=1000)
    files = ArchiveFileSerializer(many=True, max_length=10000)

    def validate(self, data):
        for rows, key in (
            (data["scenes"], "id"),
            (data["scenes"], "position"),
            (data["icons"], "key"),
            (data["files"], "path"),
        ):
            if len({row[key] for row in rows}) != len(rows):
                raise serializers.ValidationError(
                    "The project contains duplicate references."
                )
        return data
