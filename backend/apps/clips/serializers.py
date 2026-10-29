import math

from rest_framework import serializers

from apps.videomanagement.serializers.caption_words import CaptionWordSerializer
from apps.videomanagement.serializers.captions import CaptionProjectStyleSerializer
from apps.videomanagement.serializers.tags import TagTextField, VideoTagsSerializer

from .choices import ClipLayout
from .constants import MAX_CAPTION_WORDS, MAX_CLIP_DURATION, MAX_CLIPS_PER_PROJECT
from .models import Clip, ClipProject
from .uploads import validate_upload


class ProjectUploadSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=100, required=False, allow_blank=True)
    source = serializers.FileField()
    extraction_prompt = serializers.CharField(
        max_length=2000, required=False, allow_blank=True, allow_null=True
    )
    clip_count = serializers.IntegerField(min_value=1, max_value=10, default=5)
    min_duration = serializers.IntegerField(
        min_value=10, max_value=MAX_CLIP_DURATION, default=30
    )
    max_duration = serializers.IntegerField(
        min_value=10, max_value=MAX_CLIP_DURATION, default=60
    )

    def validate_extraction_prompt(self, value):
        return (value or "").strip() or None

    def validate_source(self, upload):
        self.metadata = validate_upload(upload)
        return upload

    def validate(self, data):
        if data["max_duration"] < data["min_duration"]:
            raise serializers.ValidationError(
                "Maximum length must be at least the minimum length."
            )
        if self.metadata["duration"] < data["min_duration"]:
            raise serializers.ValidationError(
                "The source video is shorter than the minimum clip length."
            )
        return data


class ClipEditSerializer(serializers.Serializer):
    revision = serializers.DateTimeField(required=False)
    title = serializers.CharField(max_length=100, required=False)
    start = serializers.FloatField(min_value=0, required=False)
    end = serializers.FloatField(min_value=0, required=False)
    layout = serializers.ChoiceField(choices=ClipLayout.choices, required=False)
    crop_position = serializers.FloatField(min_value=0, max_value=100, required=False)
    captions = serializers.BooleanField(required=False)
    words = CaptionWordSerializer(
        many=True, max_length=MAX_CAPTION_WORDS, required=False
    )
    style = CaptionProjectStyleSerializer(required=False)

    def validate(self, data):
        clip, project = self.instance, self.context["project"]
        start = data.get("start", clip.start if clip else 0)
        end = data.get("end", clip.end if clip else min(project.duration, 60))
        if not all(
            math.isfinite(value)
            for value in (start, end, data.get("crop_position", 50))
        ):
            raise serializers.ValidationError("Enter finite times and crop position.")
        if not 0 <= start < end <= project.duration or end - start > MAX_CLIP_DURATION:
            raise serializers.ValidationError(
                "Choose a clip within the source, up to 180 seconds long."
            )
        if clip is None:
            data.setdefault("start", start)
            data.setdefault("end", end)
            data.setdefault("title", "New clip")
        return data


class ClipSerializer(serializers.ModelSerializer):
    revision = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = Clip
        fields = (
            "id",
            "title",
            "reason",
            "hashtags",
            "start",
            "end",
            "layout",
            "crop_position",
            "captions",
            "words",
            "style",
            "output",
            "status",
            "error",
            "revision",
            "updated_at",
        )
        read_only_fields = fields


class ProjectSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = ClipProject
        fields = ("id", "title", "duration", "status", "error", "updated_at")
        read_only_fields = fields


class ProjectSerializer(ProjectSummarySerializer):
    clips = ClipSerializer(many=True, read_only=True)

    class Meta(ProjectSummarySerializer.Meta):
        fields = ProjectSummarySerializer.Meta.fields + (
            "source",
            "preview",
            "width",
            "height",
            "words",
            "clip_count",
            "extraction_prompt",
            "min_duration",
            "max_duration",
            "clips",
        )
        read_only_fields = fields


class CandidateSerializer(serializers.Serializer):
    first_word = serializers.IntegerField(min_value=0)
    last_word = serializers.IntegerField(min_value=0)
    title = serializers.CharField(max_length=100)
    reason = serializers.CharField(max_length=400)


class HashtagsSerializer(serializers.Serializer):
    hashtags = serializers.ListField(child=TagTextField(max_length=80), max_length=20)

    def validate_hashtags(self, values):
        tags = VideoTagsSerializer(data={"tiktok": values, "youtube": [], "search": []})
        tags.is_valid(raise_exception=True)
        values = tags.validated_data["tiktok"]
        if any(not value.isascii() for value in values):
            raise serializers.ValidationError(
                "Use English hashtags with ASCII spelling, including conventional English spellings of names."
            )
        return values


class SaveHashtagsSerializer(HashtagsSerializer):
    previous_hashtags = serializers.JSONField()


class ExportClipsSerializer(serializers.Serializer):
    clip_ids = serializers.ListField(
        child=serializers.UUIDField(), min_length=1, max_length=MAX_CLIPS_PER_PROJECT
    )
