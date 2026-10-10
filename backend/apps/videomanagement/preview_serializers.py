"""Response formatting for the video preview; timeline rules live in services.preview."""
from dataclasses import dataclass

from drf_yasg.utils import swagger_serializer_method
from rest_framework import serializers

from .models import Video
from .services.preview import PreviewTimeline, preview_timeline
from .utils.file_utils import check_if_image, check_if_video, stored_file_exists
from .video_formats import output_size


@dataclass
class PreviewData:
    video: Video
    timeline: PreviewTimeline


class PreviewCaptionSerializer(serializers.Serializer):
    start = serializers.FloatField()
    end = serializers.FloatField()
    text = serializers.CharField()


class PreviewSegmentSerializer(serializers.Serializer):
    id = serializers.SerializerMethodField()
    kind = serializers.ChoiceField(choices=("scene", "intro", "outro"))
    label = serializers.SerializerMethodField()
    text = serializers.CharField(source="content.text", allow_null=True, allow_blank=True, default=None)
    start = serializers.FloatField()
    duration = serializers.FloatField()
    base_duration = serializers.FloatField()
    pause = serializers.FloatField(source="content.pause_after", default=0)
    visual = serializers.SerializerMethodField()
    visual_type = serializers.ChoiceField(choices=("image", "video"))
    visual_duration = serializers.FloatField(allow_null=True)
    clip_audio = serializers.BooleanField()
    narration = serializers.SerializerMethodField()
    narration_duration = serializers.FloatField(allow_null=True)
    transition = serializers.ChoiceField(choices=("CUT", "FADE", "DISSOLVE"))
    transition_duration = serializers.FloatField(allow_null=True)
    fade_in = serializers.FloatField()
    fade_out = serializers.FloatField()
    dissolve_in = serializers.FloatField()

    @swagger_serializer_method(serializer_or_field=serializers.CharField())
    def get_id(self, segment):
        pk = segment.content.pk
        return str(pk) if segment.kind == "scene" else f"{segment.kind}-{pk}"

    @swagger_serializer_method(serializer_or_field=serializers.CharField())
    def get_label(self, segment):
        return f"Scene {segment.index}" if segment.kind == "scene" else segment.kind.title()

    @swagger_serializer_method(serializer_or_field=serializers.CharField(allow_null=True))
    def get_visual(self, segment):
        field = segment.image.file if segment.image else None
        if segment.kind != "scene":
            field = segment.content.file
        if not stored_file_exists(field):
            return None
        if segment.kind == "scene" and not (check_if_image(field.name) or check_if_video(field.name)):
            return None
        return field.url

    @swagger_serializer_method(serializer_or_field=serializers.CharField(allow_null=True))
    def get_narration(self, segment):
        field = segment.content.file
        return field.url if segment.narration_duration and stored_file_exists(field) else None


class PreviewTimelineSerializer(serializers.Serializer):
    """Serialize a video and its media, supplementing model fields with timeline calculations."""
    duration = serializers.FloatField(source="timeline.duration")
    size = serializers.SerializerMethodField()
    segments = PreviewSegmentSerializer(source="timeline.segments", many=True)
    captions = PreviewCaptionSerializer(source="timeline.captions", many=True)
    render_only = serializers.SerializerMethodField()

    def to_representation(self, video):
        return super().to_representation(PreviewData(video, preview_timeline(video)))

    @swagger_serializer_method(serializer_or_field=serializers.ListField(
        child=serializers.IntegerField(), min_length=2, max_length=2,
    ))
    def get_size(self, obj):
        return list(output_size((obj.video.settings or {}).get("video_format")))

    @swagger_serializer_method(serializer_or_field=serializers.ListField(child=serializers.CharField()))
    def get_render_only(self, obj):
        video = obj.video
        return [name for name, enabled in (("avatar animation", video.avatar_id),
                ("background music", video.music_id), ("background effects", video.background_id)) if enabled]
