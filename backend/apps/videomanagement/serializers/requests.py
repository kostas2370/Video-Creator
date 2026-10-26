from django.conf import settings
from django.db.models import Max
from rest_framework import serializers

from apps.videomanagement.export_settings import EXPORT_FRAME_RATES, EXPORT_PRESETS
from apps.videomanagement.integrations.visuals.registry import ImageProviderRegistry
from apps.videomanagement.services.media.selection import available_voice, owned_asset
from apps.videomanagement.services.media.uploads import validate_visual

from ..models import (
    Avatar,
    ImageMode,
    Intro,
    MotionIntensity,
    MotionStyle,
    Outro,
    TransitionStyle,
)
from ..schemas.scene_editing import SceneEditingPlanSerializer
from ..schemas.shot_planning import ShotPlanSerializer
from ..utils.file_utils import check_if_video
from ..video_formats import (
    DEFAULT_VIDEO_FORMAT,
    DEFAULT_VIDEO_PLATFORM,
    VIDEO_FORMAT_CHOICES,
    VIDEO_PLATFORM_CHOICES,
)
from .caption_styles import CaptionPresetField, CaptionStyleSerializer
from .fields import FiniteFloat, validate_image_upload


class TransitionDurationField(FiniteFloat):
    non_finite_message = "Choose a duration between 0.1 and 3 seconds."

    def __init__(self, **kwargs):
        super().__init__(min_value=0.1, max_value=3, **kwargs)


AVATAR_POSITIONS = {"left,top", "right,top", "left,bottom", "right,bottom"}


def normalize_avatar_position(value):
    """Return the canonical horizontal,vertical form used by video rendering."""
    parts = str(value or "").split(",")
    horizontal = next((part for part in parts if part in {"left", "right"}), None)
    vertical = next((part for part in parts if part in {"top", "bottom"}), None)
    normalized = f"{horizontal},{vertical}" if horizontal and vertical else ""
    if normalized not in AVATAR_POSITIONS:
        raise serializers.ValidationError(
            "Select a valid choice. Valid choices are: left,top, right,top, left,bottom, right,bottom."
        )
    return normalized


class GenerateSerializer(serializers.Serializer):
    visual_continuity = serializers.CharField(
        required=False, allow_blank=True, max_length=3000
    )
    ai_scene_editing = serializers.BooleanField(required=False, default=False)
    review_script = serializers.BooleanField(required=False, default=False)
    scene_count = serializers.IntegerField(
        required=False, allow_null=True, min_value=1, max_value=60
    )
    reference_image = serializers.ImageField(required=False)
    reference_role = serializers.ChoiceField(
        choices=("character", "style", "both"), required=False, default="both",
    )
    message = serializers.CharField(required=True, max_length=2000)
    video_format = serializers.ChoiceField(
        required=False, choices=VIDEO_FORMAT_CHOICES, default=DEFAULT_VIDEO_FORMAT
    )
    platform = serializers.ChoiceField(
        required=False, choices=VIDEO_PLATFORM_CHOICES, default=DEFAULT_VIDEO_PLATFORM
    )
    voice_id = serializers.CharField(
        required=False, max_length=36, default=None, allow_blank=True, allow_null=True
    )
    gpt_model = serializers.ChoiceField(
        required=False,
        choices=settings.ACCEPTED_MODELS,
        default=settings.DEFAULT_GPT_MODEL,
    )
    image_mode = serializers.ChoiceField(
        required=False,
        choices=[*ImageMode.choices, (False, "No visuals")],
        default=ImageMode.WEB,
    )
    avatar_selection = serializers.CharField(
        required=False, max_length=36, default="", allow_blank=True, allow_null=True
    )
    style = serializers.ChoiceField(
        required=False, choices=["vivid", "natural"], default="vivid"
    )
    music = serializers.CharField(
        required=False, max_length=500, default="", allow_blank=True, allow_null=True
    )
    target_audience = serializers.CharField(
        required=False, max_length=30, min_length=0, default="", allow_blank=True
    )
    intro = serializers.CharField(required=False, max_length=36, default=None)
    outro = serializers.CharField(required=False, max_length=36, default=None)
    subtitles = serializers.BooleanField(required=False, default=False)
    narration = serializers.BooleanField(required=False, default=True)
    provider = serializers.CharField(required=False, default=None)
    created_by = serializers.HiddenField(default=serializers.CurrentUserDefault())
    avatar_position = serializers.CharField(required=False, default="right,top")
    genre = serializers.CharField(required=False, default="", allow_blank=True)

    def validate_reference_image(self, value):
        return validate_image_upload(
            value,
            check_order=("size", "format"),
            messages={
                "size": "Choose an image smaller than 10 MB.",
                "format": "Choose a PNG, JPEG, or WebP image.",
            },
        )

    def validate(self, attrs):
        if attrs.get("reference_image") and (
            attrs.get("image_mode") != ImageMode.AI
            or not ImageProviderRegistry.supports_reference(
                attrs.get("provider"), mode=attrs.get("image_mode")
            )
        ):
            raise serializers.ValidationError(
                {
                    "reference_image": "The selected visual provider does not support reference images."
                }
            )
        attrs["avatar_position"] = normalize_avatar_position(
            attrs.get("avatar_position", "right,top")
        )
        for field, model in (
            ("avatar_selection", Avatar),
            ("intro", Intro),
            ("outro", Outro),
        ):
            owned_asset(model, attrs.get(field), attrs["created_by"])
        if not attrs.get("avatar_selection"):
            available_voice(attrs.get("voice_id"), attrs["created_by"])
        return attrs


class ManualVideoSerializer(serializers.Serializer):
    subtitles = serializers.BooleanField(default=True)
    title = serializers.CharField(max_length=50)
    video_format = serializers.ChoiceField(
        choices=VIDEO_FORMAT_CHOICES, default=DEFAULT_VIDEO_FORMAT
    )
    platform = serializers.ChoiceField(
        choices=VIDEO_PLATFORM_CHOICES, default=DEFAULT_VIDEO_PLATFORM
    )


class StoryDraftSerializer(serializers.Serializer):
    prompt = serializers.CharField(max_length=2000)


class StoryVideoSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=50)
    story = serializers.CharField(max_length=2000)
    gameplay = serializers.FileField()
    voice_id = serializers.UUIDField()
    subtitles = serializers.BooleanField(default=True)

    def validate_gameplay(self, value):
        if not check_if_video(value.name):
            raise serializers.ValidationError(
                "Choose a gameplay video: MP4, MOV, WebM, AVI, or M4V."
            )
        return validate_visual(value)

    def validate_voice_id(self, value):
        return available_voice(value, self.context["request"].user)


class SceneDraftSerializer(serializers.Serializer):
    prompt = serializers.CharField(max_length=2000)
    use_context = serializers.BooleanField(default=False)
    draft_type = serializers.ChoiceField(
        choices=["sentence", "section", "story"], default="sentence"
    )
    sentence_count = serializers.IntegerField(default=1, min_value=1, max_value=12)

    def validate(self, attrs):
        if attrs["draft_type"] == "sentence" and attrs["sentence_count"] != 1:
            raise serializers.ValidationError(
                "A sentence draft contains exactly one sentence."
            )
        return attrs


class ManualTextSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=2000, allow_blank=True)


class SceneUpdateSerializer(serializers.Serializer):
    text = serializers.CharField(required=True, max_length=2000)


class ChangeSceneImageSerializer(serializers.Serializer):
    image = serializers.FileField(required=False)
    with_audio = serializers.BooleanField(default=False)

    def validate_image(self, value):
        return validate_visual(value)

    def validate(self, attrs):
        if not self.context.get("has_scene_image") and "image" not in attrs:
            raise serializers.ValidationError({"image": "You must add an image!"})
        return attrs


class SceneImageQuerySerializer(serializers.Serializer):
    scene_image = serializers.UUIDField(required=False)


class GenerateSceneImageSerializer(serializers.Serializer):
    image_description = serializers.CharField(max_length=2000)


class RenderVideoSerializer(serializers.Serializer):
    export_preset = serializers.ChoiceField(choices=tuple(EXPORT_PRESETS), required=False)
    export_fps = serializers.ChoiceField(choices=EXPORT_FRAME_RATES, required=False)


class VideoUpdateSerializer(serializers.Serializer):
    visual_continuity = serializers.CharField(
        required=False, allow_blank=True, max_length=3000
    )
    intro_transition = serializers.ChoiceField(
        choices=TransitionStyle.choices, required=False
    )
    intro_transition_duration = TransitionDurationField(required=False, allow_null=True)
    voice_id = serializers.UUIDField(required=False)
    transition_default = serializers.ChoiceField(
        choices=[
            choice
            for choice in TransitionStyle.choices
            if choice[0] != TransitionStyle.DEFAULT
        ],
        required=False,
    )
    transition_duration = TransitionDurationField(required=False, allow_null=True)
    avatar = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    intro = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    outro = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    title = serializers.CharField(required=False, max_length=50)
    video_format = serializers.ChoiceField(choices=VIDEO_FORMAT_CHOICES, required=False)
    platform = serializers.ChoiceField(choices=VIDEO_PLATFORM_CHOICES, required=False)
    subtitles = serializers.BooleanField(required=False)
    caption_style = CaptionPresetField(required=False)
    caption_config = CaptionStyleSerializer(required=False)
    avatar_position = serializers.CharField(required=False)

    def validate_avatar_position(self, value):
        return normalize_avatar_position(value)


class ScenePositionSerializer(serializers.Serializer):
    position = serializers.IntegerField(required=False, allow_null=True, min_value=1)

    def validate_position(self, position):
        video = self.context.get("video")
        if position is not None and video is not None:
            last = video.scenes.aggregate(last=Max("position"))["last"] or 0
            if position > last + 1:
                raise serializers.ValidationError(
                    "Choose a position within the current video."
                )
        return position


class ManualSceneSerializer(ScenePositionSerializer):
    text = serializers.CharField(
        required=False, allow_blank=True, max_length=2000, default=""
    )
    image = serializers.FileField(required=False)
    duration = FiniteFloat(
        min_value=0.1, max_value=900, required=False, allow_null=True
    )
    with_audio = serializers.BooleanField(default=True)

    def validate_image(self, value):
        return validate_visual(value)


class AddSceneSerializer(ScenePositionSerializer):
    text = serializers.CharField(required=False)
    image_description = serializers.CharField(required=False)
    is_last = serializers.BooleanField(default=False)
    with_audio = serializers.BooleanField(default=False)

    def validate(self, attrs):
        if not attrs.get("text"):
            raise serializers.ValidationError("text field required !")

        return super().validate(attrs)


class AddScenesSerializer(ScenePositionSerializer):
    scenes = AddSceneSerializer(many=True, min_length=1, max_length=12)


class StoryboardSentenceSerializer(serializers.Serializer):
    shot_plan = ShotPlanSerializer(required=False)
    editing = SceneEditingPlanSerializer(required=False)
    sentence = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    image_description = serializers.CharField(max_length=2000)


class StoryboardSceneSerializer(serializers.Serializer):
    scene = serializers.CharField(max_length=200)
    sentences = StoryboardSentenceSerializer(many=True, min_length=1, max_length=60)


class StoryboardSerializer(serializers.Serializer):
    visual_continuity = serializers.CharField(
        required=False, allow_blank=True, max_length=3000,
    )
    title = serializers.CharField(max_length=50)
    target_audience = serializers.CharField(
        required=False, allow_blank=True, max_length=2000
    )
    topic = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    scenes = StoryboardSceneSerializer(many=True, min_length=1, max_length=60)

    def validate_scenes(self, scenes):
        if sum(len(scene["sentences"]) for scene in scenes) > 120:
            raise serializers.ValidationError("Use at most 120 shots.")
        if self.context.get("narration", True) and any(
            not sentence.get("sentence", "").strip()
            for scene in scenes
            for sentence in scene["sentences"]
        ):
            raise serializers.ValidationError("Add narration for each shot.")
        return scenes


class ReorderScenesSerializer(serializers.Serializer):
    expected_scene_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, allow_empty=True
    )
    scene_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)

    def validate_scene_ids(self, values):
        if len(set(values)) != len(values):
            raise serializers.ValidationError("Include each scene exactly once.")
        return values


class RestoreSceneSerializer(ReorderScenesSerializer):
    scene_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, allow_empty=False
    )
    expected_scene_ids = serializers.ListField(
        child=serializers.UUIDField(), allow_empty=True
    )


class SceneOrderSerializer(serializers.Serializer):
    scene_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=True)


class SceneTransitionSerializer(serializers.Serializer):
    transition_after = serializers.ChoiceField(choices=TransitionStyle.choices)
    transition_duration = TransitionDurationField(required=False, allow_null=True)


class BulkAutoMotionSerializer(serializers.Serializer):
    motion_intensity = serializers.ChoiceField(choices=MotionIntensity.choices)


class SceneMotionSerializer(serializers.Serializer):
    motion_style = serializers.ChoiceField(choices=MotionStyle.choices)
    motion_intensity = serializers.ChoiceField(
        choices=MotionIntensity.choices, required=False
    )


class SceneTimingSerializer(serializers.Serializer):
    duration = FiniteFloat(
        min_value=0.1, max_value=900, required=False, allow_null=True
    )
    pause_after = FiniteFloat(min_value=0, max_value=10, required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(
                "Supply a duration or a pause to update timing."
            )
        return attrs


class SceneJobQuerySerializer(serializers.Serializer):
    job = serializers.CharField(max_length=512)


class VideoNotesSerializer(serializers.Serializer):
    notes = serializers.CharField(
        allow_blank=True, max_length=10000, trim_whitespace=False
    )
    previous_notes = serializers.CharField(
        allow_blank=True, max_length=10000, trim_whitespace=False, write_only=True
    )
