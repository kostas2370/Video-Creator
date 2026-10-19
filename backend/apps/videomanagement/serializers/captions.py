from ..services.caption_styles import FONTS
import math
import re
import subprocess
import tempfile
from pathlib import Path

from rest_framework import serializers

from ..models import CaptionProject
from ..utils.timing import video_metadata


class CaptionUploadSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=100, required=False, allow_blank=True)
    source = serializers.FileField()

    def validate_source(self, upload):
        if upload.size > 100 * 1024 * 1024:
            raise serializers.ValidationError("Choose a video smaller than 100 MB.")
        suffix = Path(upload.name).suffix.lower()
        if suffix not in {".mp4", ".mov", ".webm", ".m4v"}:
            raise serializers.ValidationError("Choose an MP4, MOV, WebM, or M4V video.")
        try:
            with tempfile.NamedTemporaryFile(suffix=suffix) as file:
                for chunk in upload.chunks():
                    file.write(chunk)
                file.flush()
                metadata = video_metadata(file.name)
            if metadata["duration"] > 900:
                raise serializers.ValidationError("Choose a video up to 15 minutes long.")
            if not metadata["audio"]:
                raise serializers.ValidationError("This video has no audio to transcribe.")
            if not all(0 < metadata[key] <= 3840 for key in ("width", "height")):
                raise serializers.ValidationError("Choose a video with dimensions up to 3840 pixels.")
            self.metadata = metadata
        except (OSError, ValueError, KeyError, StopIteration, subprocess.SubprocessError):
            raise serializers.ValidationError("Could not read this video. Try another file.")
        finally:
            upload.seek(0)
        return upload


class CaptionWordSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=40)
    start = serializers.FloatField(min_value=0)
    end = serializers.FloatField(min_value=0)

    def validate(self, data):
        if re.search(r"\s", data["text"]):
            raise serializers.ValidationError("Edit one word at a time; add a row for another word.")
        if not all(math.isfinite(data[key]) for key in ("start", "end")) or data["end"] <= data["start"]:
            raise serializers.ValidationError("End time must be later than start time.")
        return data


class CaptionStyleSerializer(serializers.Serializer):
    preset = serializers.ChoiceField(choices=("TIKTOK", "CLASSIC"), default="TIKTOK")
    font = serializers.ChoiceField(choices=FONTS, default="DejaVu Sans")
    size = serializers.IntegerField(min_value=3, max_value=9, default=6)
    color = serializers.RegexField(r"^#[0-9a-fA-F]{6}$", default="#ffffff")
    highlight = serializers.RegexField(r"^#[0-9a-fA-F]{6}$", default="#ffe846")
    position = serializers.ChoiceField(choices=("bottom", "middle", "top"), default="bottom")


class CaptionEditSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=100, required=False)
    words = CaptionWordSerializer(many=True, required=False, max_length=10000)
    style = CaptionStyleSerializer(required=False)

    def validate_words(self, words):
        previous_end = 0
        for word in words:
            if word["start"] < previous_end or word["end"] > self.instance.duration + 0.01:
                raise serializers.ValidationError("Words must be in order, without overlap, and within the video duration.")
            previous_end = word["end"]
        return words


class CaptionProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = CaptionProject
        fields = ("id", "title", "source", "preview", "output", "words", "style", "duration", "width", "height", "status", "error", "updated_at")
        read_only_fields = fields


class CaptionProjectSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = CaptionProject
        fields = ("id", "title", "duration", "status", "updated_at")
        read_only_fields = fields
