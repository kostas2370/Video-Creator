import math

from django.utils import timezone
from rest_framework import serializers
from rest_framework.reverse import reverse

from apps.videomanagement.serializers.caption_words import CaptionWordSerializer
from apps.videomanagement.serializers.captions import CaptionProjectStyleSerializer
from apps.videomanagement.serializers.tags import TagTextField, VideoTagsSerializer

from .choices import CLIP_BUSY, PROJECT_BUSY, ClipLayout, ClipProjectStatus, ClipStatus
from .constants import (
    EXPORT_STALE_AFTER,
    MAX_CAPTION_WORDS,
    MAX_CLIP_DURATION,
    MAX_CLIPS_PER_PROJECT,
    PROJECT_STALE_AFTER,
)
from .models import Clip, ClipProject
from .transcripts import validate_range
from .uploads import validate_upload
from .youtube import youtube_url


class ProjectUploadSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=100, required=False, allow_blank=True)
    source = serializers.FileField(required=False)
    youtube_url = serializers.CharField(
        max_length=500, required=False, allow_blank=True
    )
    extraction_prompt = serializers.CharField(
        max_length=2000, required=False, allow_blank=True, allow_null=True
    )
    range_start = serializers.FloatField(min_value=0, default=0)
    range_end = serializers.FloatField(min_value=0, required=False, allow_null=True)
    clip_count = serializers.IntegerField(min_value=1, max_value=10, default=5)
    min_duration = serializers.IntegerField(
        min_value=10, max_value=MAX_CLIP_DURATION, default=30
    )
    max_duration = serializers.IntegerField(
        min_value=10, max_value=MAX_CLIP_DURATION, default=60
    )

    def validate_youtube_url(self, value):
        return youtube_url(value) if value else ""

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
        if bool(data.get("source")) == bool(data.get("youtube_url")):
            raise serializers.ValidationError(
                "Choose either a video file or a YouTube link."
            )
        if data.get("source") and self.metadata["duration"] < data["min_duration"]:
            raise serializers.ValidationError(
                "The source video is shorter than the minimum clip length."
            )
        validate_range(
            data["range_start"],
            data.get("range_end"),
            data["min_duration"],
            self.metadata["duration"] if data.get("source") else None,
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
        start = data.get("start", clip.start if clip else project.range_start)
        end = data.get(
            "end",
            clip.end if clip else min(project.range_stop, project.range_start + 60),
        )
        if not all(
            math.isfinite(value)
            for value in (start, end, data.get("crop_position", 50))
        ):
            raise serializers.ValidationError("Enter finite times and crop position.")
        if (
            not project.range_start <= start < end <= project.range_stop
            or end - start > MAX_CLIP_DURATION
        ):
            raise serializers.ValidationError(
                "Choose a clip within the processing range, up to 180 seconds long."
            )
        if clip is None:
            data.setdefault("start", start)
            data.setdefault("end", end)
            data.setdefault("title", "New clip")
        return data


class ClipSerializer(serializers.ModelSerializer):
    output = serializers.SerializerMethodField()
    can_retry = serializers.SerializerMethodField()

    def get_output(self, clip):
        return (
            reverse(
                "clipproject-output",
                kwargs={"pk": clip.project_id, "clip_id": clip.pk},
                request=self.context.get("request"),
            )
            if clip.output
            else None
        )

    def get_can_retry(self, clip):
        return clip.status == ClipStatus.FAILED or (
            clip.status in CLIP_BUSY
            and clip.updated_at <= timezone.now() - EXPORT_STALE_AFTER
        )

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
            "can_retry",
        )
        read_only_fields = fields


class ProjectSummarySerializer(serializers.ModelSerializer):
    clip_total = serializers.IntegerField(read_only=True)
    export_total = serializers.IntegerField(read_only=True)
    source_type = serializers.SerializerMethodField()

    def get_source_type(self, project):
        return "youtube" if project.youtube_url else "upload"

    can_retry = serializers.SerializerMethodField()

    def get_can_retry(self, project):
        return project.status == ClipProjectStatus.FAILED or (
            project.status in PROJECT_BUSY
            and project.updated_at <= timezone.now() - PROJECT_STALE_AFTER
        )

    class Meta:
        model = ClipProject
        fields = (
            "id",
            "title",
            "duration",
            "status",
            "error",
            "updated_at",
            "can_retry",
            "created_at",
            "clip_total",
            "export_total",
            "source_type",
        )
        read_only_fields = fields


class ProjectSerializer(ProjectSummarySerializer):
    source = serializers.SerializerMethodField()
    preview = serializers.SerializerMethodField()

    def get_source(self, project):
        return (
            reverse(
                "clipproject-source",
                kwargs={"pk": project.pk},
                request=self.context.get("request"),
            )
            if project.source
            else None
        )

    def get_preview(self, project):
        return (
            reverse(
                "clipproject-preview",
                kwargs={"pk": project.pk},
                request=self.context.get("request"),
            )
            if project.preview
            else None
        )

    clips = ClipSerializer(many=True, read_only=True)

    class Meta(ProjectSummarySerializer.Meta):
        fields = ProjectSummarySerializer.Meta.fields + (
            "source",
            "youtube_url",
            "range_start",
            "range_end",
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


class ClipProgressSerializer(ClipSerializer):
    class Meta(ClipSerializer.Meta):
        fields = ("id", "status", "error", "revision", "hashtags", "can_retry")
        read_only_fields = fields


class ProjectProgressSerializer(ProjectSerializer):
    clips = ClipProgressSerializer(many=True, read_only=True)
    has_transcript = serializers.BooleanField(read_only=True)

    class Meta(ProjectSummarySerializer.Meta):
        fields = ProjectSummarySerializer.Meta.fields + (
            "clips",
            "has_transcript",
            "source",
            "preview",
            "width",
            "height",
        )
        read_only_fields = fields


class TranscriptSearchSerializer(serializers.Serializer):
    prompt = serializers.CharField(max_length=2000)
