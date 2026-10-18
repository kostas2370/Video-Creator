"""Response formatting for the video preview; timeline rules live in services.preview."""
from dataclasses import dataclass

from drf_yasg.utils import swagger_serializer_method
from rest_framework import serializers

from ..models import Video, TransitionStyle, MotionStyle, MotionIntensity
from ..services.preview import PreviewTimeline, preview_timeline
from ..utils.file_utils import check_if_image, check_if_video, stored_file_exists
from ..video_formats import output_size
from ..utils.audio_editing import narration_file, voice_tracks

from ..utils.motion import resolved_motion


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
    transition = serializers.ChoiceField(choices=[choice for choice in TransitionStyle.choices if choice[0] != TransitionStyle.DEFAULT])
    transition_duration = serializers.FloatField(allow_null=True)
    motion_style = serializers.SerializerMethodField()
    motion_intensity = serializers.CharField(source="content.motion_intensity", default=MotionIntensity.SUBTLE)
    overlays = serializers.JSONField(source="content.overlays", default=list)
    overlay_logo = serializers.FileField(source="content.overlay_logo", default=None, allow_null=True)
    fade_in = serializers.FloatField()
    fade_out = serializers.FloatField()
    dissolve_in = serializers.FloatField()

    @swagger_serializer_method(serializer_or_field=serializers.CharField())
    def get_motion_style(self, segment):
        return resolved_motion(segment.content) if segment.kind == "scene" and segment.visual_type == "image" else MotionStyle.NONE

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
        field = narration_file(segment.content)
        return field.url if segment.narration_duration and stored_file_exists(field) else None


class PreviewTimelineSerializer(serializers.Serializer):
    """Serialize a video and its media, supplementing model fields with timeline calculations."""
    duration = serializers.FloatField(source="timeline.duration")
    size = serializers.SerializerMethodField()
    segments = PreviewSegmentSerializer(source="timeline.segments", many=True)
    captions = PreviewCaptionSerializer(source="timeline.captions", many=True)
    render_only = serializers.SerializerMethodField()
    audio_tracks = serializers.SerializerMethodField()
    music = serializers.SerializerMethodField()

    def get_audio_tracks(self, obj):
        return voice_tracks(obj.timeline.segments)

    def get_music(self, obj):
        music = obj.video.music
        if not music or not stored_file_exists(music.file):
            return None
        segments = [s for s in obj.timeline.segments if s.kind == "scene"]
        return {"source": music.file.url, "start": segments[0].start,
                "duration": sum(s.duration for s in segments),
                "settings": {key: value for key, value in (obj.video.settings or {}).items()
                             if key.startswith("music_") or key.startswith("duck_")}}


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
        return ["avatar animation"] if video.avatar_id else []
