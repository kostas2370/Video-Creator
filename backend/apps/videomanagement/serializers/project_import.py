"""Input schema for portable project archives; archive IDs are references only."""

from rest_framework import serializers

from apps.videomanagement.models import MediaAsset, Video

from .audio import MusicAudioSerializer
from .caption_words import CaptionWordSerializer
from .covers import CoverSerializer
from .fields import FiniteFloat
from .project_export import ProjectSceneAudioSerializer, ProjectSceneSerializer
from .requests import SceneCutsSerializer, StoryboardSerializer, VideoUpdateSerializer

MAX_PROJECT_BYTES = 1024 * 1024 * 1024


class ProjectImportUploadSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, upload):
        if upload.size > MAX_PROJECT_BYTES:
            raise serializers.ValidationError("Choose a project ZIP smaller than 1 GB.")
        return upload


class ArchiveFileSerializer(serializers.Serializer):
    path = serializers.RegexField(r"\Amedia/[a-zA-Z0-9_-]+\.[a-zA-Z0-9]{1,10}\Z")
    size = serializers.IntegerField(min_value=0, max_value=MAX_PROJECT_BYTES)
    sha256 = serializers.RegexField(r"\A[a-f0-9]{64}\Z")


class ArchiveLicenseSerializer(serializers.Serializer):
    attribution = serializers.CharField(allow_blank=True, max_length=10000)
    license_url = serializers.URLField(allow_blank=True, max_length=500)
    source_url = serializers.URLField(allow_blank=True, max_length=500, required=False)


class ArchiveResourceSerializer(serializers.Serializer):
    id = serializers.UUIDField(required=False)
    name = serializers.CharField(max_length=140, allow_blank=True)
    file = serializers.CharField(allow_null=True)
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


class ArchiveCutsSerializer(SceneCutsSerializer):
    previous = serializers.JSONField(required=False)
    source_key = serializers.RegexField(r"\A[a-f0-9]{64}\Z", required=False)


class ArchiveAudioSerializer(ProjectSceneAudioSerializer):
    duration = FiniteFloat(
        min_value=0.1, max_value=900, required=False, allow_null=True
    )


class ArchiveSceneSerializer(ProjectSceneSerializer):
    id = serializers.UUIDField()
    position = serializers.IntegerField(min_value=1, max_value=2147483647)
    script_index = serializers.IntegerField(
        min_value=0, max_value=2147483647, allow_null=True
    )
    text = serializers.CharField(allow_blank=True, max_length=100000)
    caption_alignment = ArchiveAlignmentSerializer()
    audio_settings = ArchiveAudioSerializer()
    pause_after = FiniteFloat(min_value=0, max_value=10)
    transition_duration = FiniteFloat(min_value=0, max_value=10, allow_null=True)
    cuts = serializers.JSONField()
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

    def validate_cuts(self, value):
        return validate_cuts(value)


def validate_cuts(value):
    if value == {}:
        return {}
    serializer = ArchiveCutsSerializer(data=value)
    serializer.is_valid(raise_exception=True)
    return {
        key: data
        for key, data in serializer.validated_data.items()
        if key != "previous"
    }


class ArchiveSettingsSerializer(VideoUpdateSerializer, MusicAudioSerializer):
    export_preset = serializers.ChoiceField(
        choices=("DRAFT", "STANDARD", "HIGH"), required=False
    )
    export_fps = serializers.ChoiceField(choices=(24, 30), required=False)
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


class ArchiveCoverSerializer(CoverSerializer):
    def validate(self, data):
        return data


class ArchiveProjectSerializer(serializers.ModelSerializer):
    prompt = serializers.CharField(allow_blank=True, max_length=100000)
    settings = serializers.JSONField()
    storyboard = StoryboardSerializer(allow_null=True)
    source_audio_duration = FiniteFloat(min_value=0, allow_null=True)
    source_audio_words = CaptionWordSerializer(many=True, max_length=10000)
    cuts = serializers.JSONField()
    cover_settings = serializers.JSONField()
    avatar = ArchiveResourceSerializer(allow_null=True)
    intro = ArchiveResourceSerializer(allow_null=True)
    outro = ArchiveResourceSerializer(allow_null=True)
    music = ArchiveResourceSerializer(allow_null=True)
    reference_image = serializers.CharField(allow_null=True)
    source_audio = serializers.CharField(allow_null=True)
    cover = serializers.CharField(allow_null=True)
    thumbnail = serializers.CharField(allow_null=True)
    output = serializers.CharField(allow_null=True)

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
            "cuts",
            "cover_settings",
            "source_audio_duration",
            "source_audio_words",
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

    def validate(self, data):
        for key in ("avatar", "intro", "outro"):
            if data[key] and len(data[key]["name"]) > 100:
                raise serializers.ValidationError(
                    {key: "Use a name of at most 100 characters."}
                )
        return data

    def validate_settings(self, value):
        editable = ArchiveSettingsSerializer(data=value)
        editable.is_valid(raise_exception=True)
        data = dict(editable.validated_data)
        for key in ("voice_id", "narration_scenes", "retry_narration"):
            data.pop(key, None)
        return data

    def validate_cuts(self, value):
        return validate_cuts(value)

    def validate_cover_settings(self, value):
        if value == {}:
            return {}
        serializer = ArchiveCoverSerializer(data=value, partial=True)
        serializer.is_valid(raise_exception=True)
        return {
            key: data
            for key, data in serializer.validated_data.items()
            if key != "image"
        }


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
