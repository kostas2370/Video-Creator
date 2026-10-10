from drf_yasg.utils import swagger_serializer_method
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from .utils.file_utils import check_if_image, check_if_video, stored_file_exists
from .utils.timing import file_timing, scene_timing
from .services.preview import preview_timeline
from .video_formats import output_size

from .models import (
    TemplatePrompt,
    Music,
    Scene,
    SceneImage,
    VoiceModel,
    Avatar,
    UserPrompt,
    Video,
    Intro,
    Outro,
)


class TemplatePromptsSerializer(serializers.ModelSerializer):
    created_by = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = TemplatePrompt
        fields = "__all__"
        validators = [
            UniqueTogetherValidator(
                queryset=TemplatePrompt.objects.all(),
                fields=["created_by", "title"],
                message="You already have a template with this name.",
            )
        ]


class MusicSerializer(serializers.ModelSerializer):
    created_by = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Music
        fields = "__all__"


class SceneImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SceneImage
        exclude = ("scene",)


class SceneSerializer(serializers.ModelSerializer):
    scene_image = serializers.SerializerMethodField()
    narration_status = serializers.SerializerMethodField()
    timing = serializers.SerializerMethodField()

    def get_timing(self, obj):
        return scene_timing(obj, next(iter(obj.scene_images.all()), None))

    def get_narration_status(self, obj):
        video = obj.video
        if not (video.settings or {}).get("narration", True):
            return "disabled"
        return "available" if stored_file_exists(obj.file) else "missing"

    class Meta:
        model = Scene
        fields = "__all__"

    def get_scene_image(self, obj):
        image = next(iter(obj.scene_images.all()), None)

        return SceneImageSerializer(image).data if image else ""


class VoiceModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = VoiceModel
        fields = ("id", "created_by", "name", "provider", "type", "sample", "path")
        read_only_fields = fields


class AvatarNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Avatar
        fields = "__all__"


class AvatarSerializer(serializers.ModelSerializer):
    sample = serializers.SerializerMethodField()
    created_by = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Avatar
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        self.fields["voice"].queryset = (
            VoiceModel.available_to(request.user) if request else VoiceModel.objects.none()
        )

    def get_sample(self, obj):
        return obj.voice.sample if obj.voice else ""


class UserPromptSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPrompt
        fields = "__all__"


VIDEO_RESPONSE_FIELDS = (
    "id", "created_by", "title", "url", "gpt_answer", "prompt", "genre", "output",
    "dir_name", "voice_model", "avatar", "status", "updated_at", "music",
    "background", "intro", "outro", "video_type", "mode", "settings",
)


class VideoSerializer(serializers.ModelSerializer):
    prompt = UserPromptSerializer(read_only=True)
    music = serializers.SerializerMethodField()

    class Meta:
        model = Video
        fields = VIDEO_RESPONSE_FIELDS
        read_only_fields = fields

    def get_music(self, obj):
        if obj.music:
            return obj.music.name

        return ""


class VideoNestedSerializer(serializers.ModelSerializer):
    prompt = UserPromptSerializer(read_only=True)
    scenes = serializers.SerializerMethodField()
    extra_duration = serializers.SerializerMethodField()

    def get_extra_duration(self, obj):
        durations = [file_timing(asset.file).get("duration") for asset in (obj.intro, obj.outro) if asset]
        return sum(durations) if all(value is not None for value in durations) else None

    class Meta:
        model = Video
        fields = (*VIDEO_RESPONSE_FIELDS, "scenes", "extra_duration")
        read_only_fields = fields

    def get_scenes(self, obj):
        scenes = obj.scenes.all()
        return SceneSerializer(scenes, many=True).data


class IntroSerializer(serializers.ModelSerializer):
    created_by = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Intro
        fields = "__all__"


class OutroSerializer(serializers.ModelSerializer):
    created_by = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Outro
        fields = "__all__"


class PreviewCaptionSerializer(serializers.Serializer):
    start = serializers.FloatField()
    end = serializers.FloatField()
    text = serializers.CharField()


class PreviewSegmentSerializer(serializers.Serializer):
    id = serializers.SerializerMethodField()
    kind = serializers.ChoiceField(choices=("scene", "intro", "outro"))
    label = serializers.SerializerMethodField()
    text = serializers.CharField(source="source.text", allow_null=True, allow_blank=True, default=None)
    start = serializers.FloatField()
    duration = serializers.FloatField()
    base_duration = serializers.FloatField()
    pause = serializers.FloatField(source="source.pause_after", default=0)
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
        pk = segment.source.pk
        return str(pk) if segment.kind == "scene" else f"{segment.kind}-{pk}"

    @swagger_serializer_method(serializer_or_field=serializers.CharField())
    def get_label(self, segment):
        return f"Scene {segment.index}" if segment.kind == "scene" else segment.kind.title()

    @swagger_serializer_method(serializer_or_field=serializers.CharField(allow_null=True))
    def get_visual(self, segment):
        field = segment.image.file if segment.image else None
        if segment.kind != "scene":
            field = segment.source.file
        if not stored_file_exists(field):
            return None
        if segment.kind == "scene" and not (check_if_image(field.name) or check_if_video(field.name)):
            return None
        return field.url

    @swagger_serializer_method(serializer_or_field=serializers.CharField(allow_null=True))
    def get_narration(self, segment):
        field = segment.source.file
        return field.url if segment.narration_duration and stored_file_exists(field) else None


class PreviewTimelineSerializer(serializers.Serializer):
    """Serialize a video and its media, supplementing model fields with timeline calculations."""
    duration = serializers.FloatField(source="timeline.duration")
    size = serializers.SerializerMethodField()
    segments = PreviewSegmentSerializer(source="timeline.segments", many=True)
    captions = PreviewCaptionSerializer(source="timeline.captions", many=True)
    render_only = serializers.SerializerMethodField()

    def to_representation(self, video):
        return super().to_representation({"video": video, "timeline": preview_timeline(video)})

    @swagger_serializer_method(serializer_or_field=serializers.ListField(
        child=serializers.IntegerField(), min_length=2, max_length=2,
    ))
    def get_size(self, obj):
        return list(output_size((obj["video"].settings or {}).get("video_format")))

    @swagger_serializer_method(serializer_or_field=serializers.ListField(child=serializers.CharField()))
    def get_render_only(self, obj):
        video = obj["video"]
        return [name for name, enabled in (("avatar animation", video.avatar_id),
                ("background music", video.music_id), ("background effects", video.background_id)) if enabled]
