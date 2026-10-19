from rest_framework import serializers

from ..models import CaptionProject
from ..services.caption_styles import CAPTION_STYLES, FONTS
from ..services.caption_timing import validate_word_bounds
from ..services.caption_uploads import validate_caption_upload
from .caption_words import CaptionWordSerializer


class CaptionUploadSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=100, required=False, allow_blank=True)
    source = serializers.FileField()

    def validate_source(self, upload):
        self.metadata = validate_caption_upload(upload)
        return upload


class CaptionProjectStyleSerializer(serializers.Serializer):
    preset = serializers.ChoiceField(choices=tuple(CAPTION_STYLES), default="TIKTOK")
    font = serializers.ChoiceField(choices=FONTS, default="DejaVu Sans")
    size = serializers.IntegerField(min_value=3, max_value=9, default=6)
    color = serializers.RegexField(r"^#[0-9a-fA-F]{6}$", default="#ffffff")
    highlight = serializers.RegexField(r"^#[0-9a-fA-F]{6}$", default="#ffe846")
    position = serializers.ChoiceField(choices=("bottom", "middle", "top"), default="bottom")


class CaptionEditSerializer(serializers.Serializer):
    revision = serializers.DateTimeField()
    title = serializers.CharField(max_length=100, required=False)
    words = CaptionWordSerializer(many=True, required=False, max_length=10000)
    style = CaptionProjectStyleSerializer(required=False)

    def validate_words(self, words):
        return validate_word_bounds(words, self.instance.duration)


class CaptionProjectSerializer(serializers.ModelSerializer):
    revision = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = CaptionProject
        fields = (
            "id", "title", "source", "preview", "output", "words", "style",
            "duration", "width", "height", "status", "error", "updated_at", "revision",
        )
        read_only_fields = fields


class CaptionProjectSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = CaptionProject
        fields = ("id", "title", "duration", "status", "updated_at")
        read_only_fields = fields
