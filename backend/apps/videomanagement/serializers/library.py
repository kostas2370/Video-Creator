from pathlib import Path
import tempfile

from PIL import Image
from rest_framework import serializers

from ..models import MediaAsset
from ..services.caption_styles import FONTS
from ..utils.file_utils import check_if_image, check_if_video
from ..utils.timing import media_timing
from .audio import FiniteFloat
from .requests import validate_visual


class MediaAssetSerializer(serializers.ModelSerializer):
    tags = serializers.JSONField(required=False)

    class Meta:
        model = MediaAsset
        fields = ("id", "title", "file", "kind", "tags", "duration", "created_at")
        read_only_fields = ("id", "kind", "duration", "created_at")

    def validate_tags(self, value):
        if not isinstance(value, list) or len(value) > 12 or any(not isinstance(tag, str) or not tag.strip() or len(tag.strip()) > 30 for tag in value):
            raise serializers.ValidationError("Use up to 12 tags, each 1–30 characters long.")
        return list(dict.fromkeys(tag.strip().lower() for tag in value))

    def validate(self, attrs):
        upload = attrs.get("file")
        if self.instance and upload:
            raise serializers.ValidationError({"file": "Upload a new library item to use a different file."})
        if not upload:
            return attrs
        if upload.size > 100 * 1024 * 1024:
            raise serializers.ValidationError({"file": "Choose a file up to 100 MB."})
        suffix = Path(upload.name).suffix.lower()
        if check_if_image(upload.name) or check_if_video(upload.name):
            validate_visual(upload)
            attrs["kind"] = "IMAGE" if check_if_image(upload.name) else "VIDEO"
            if attrs["kind"] == "IMAGE":
                with Image.open(upload) as image:
                    if image.width * image.height > 16000000:
                        raise serializers.ValidationError({"file": "Use an image with at most 16 million pixels."})
                upload.seek(0)
        elif suffix in (".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"):
            attrs["kind"] = "AUDIO"
        else:
            raise serializers.ValidationError({"file": "Choose an image, video, MP3, WAV, M4A, AAC, OGG, or FLAC file."})
        if attrs["kind"] != "IMAGE":
            with tempfile.NamedTemporaryFile(suffix=suffix) as temporary:
                for chunk in upload.chunks():
                    temporary.write(chunk)
                temporary.flush()
                metadata = media_timing(temporary.name)
            upload.seek(0)
            duration = metadata.get("audio_duration" if attrs["kind"] == "AUDIO" else "duration")
            if not duration or duration > 900:
                raise serializers.ValidationError({"file": "Choose playable media up to 15 minutes long."})
            attrs["duration"] = duration
        return attrs


class UseMediaSerializer(serializers.Serializer):
    video_id = serializers.UUIDField()
    purpose = serializers.ChoiceField(choices=("new_scene", "visual", "music"))
    scene_id = serializers.UUIDField(required=False)
    text = serializers.CharField(required=False, allow_blank=True, max_length=2000, default="")
    duration = FiniteFloat(required=False, min_value=0.1, max_value=900)
    position = serializers.IntegerField(required=False, min_value=1)
    with_audio = serializers.BooleanField(default=False)


class CoverSerializer(serializers.Serializer):
    time = FiniteFloat(min_value=0, max_value=86400, default=0)
    title = serializers.CharField(max_length=100, allow_blank=True, default="", trim_whitespace=False)
    font = serializers.ChoiceField(choices=FONTS, default="Poppins")
    color = serializers.RegexField(r"^#[0-9a-fA-F]{6}$", default="#ffffff")
    position = serializers.ChoiceField(choices=("top", "middle", "bottom"), default="bottom")
    size = FiniteFloat(min_value=3, max_value=16, default=8)
    background = serializers.BooleanField(default=True)
