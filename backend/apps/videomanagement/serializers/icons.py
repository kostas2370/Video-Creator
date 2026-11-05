import io
from uuid import uuid4

from django.core.files.base import ContentFile
from PIL import Image, ImageOps
from rest_framework import serializers

from apps.videomanagement.models import Icon

from .fields import validate_image_upload


class IconSerializer(serializers.ModelSerializer):
    file = serializers.ImageField()
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)
    is_owner = serializers.SerializerMethodField()

    def get_is_owner(self, icon) -> bool:
        return icon.created_by_id == self.context["request"].user.pk

    class Meta:
        model = Icon
        fields = ("key", "collection", "name", "description", "file", "license", "license_url", "attribution", "is_owner")
        read_only_fields = ("key", "collection", "license", "license_url", "attribution")

    def validate_file(self, upload):
        return validate_image_upload(
            upload, max_pixels=4_000_000, still_only=True,
            messages={
                "size": "Use an icon smaller than 10 MB.",
                "pixels": "Use an icon with at most 4 million pixels.",
                "format": "Use a PNG, JPEG or WebP icon.",
                "animated": "Use a still image for your icon.",
            },
        )

    def create(self, validated_data):
        upload = validated_data.pop("file")
        upload.seek(0)
        with Image.open(upload) as source:
            image = ImageOps.contain(ImageOps.exif_transpose(source).convert("RGBA"), (256, 256), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (256, 256))
        canvas.alpha_composite(image, ((256 - image.width) // 2, (256 - image.height) // 2))
        output = io.BytesIO()
        canvas.save(output, format="PNG")
        identifier = uuid4().hex
        icon = Icon(key=f"custom:{identifier}", collection="custom", created_by=self.context["request"].user, **validated_data)
        icon.file.save(f"custom/{identifier}.png", ContentFile(output.getvalue()), save=False)
        try:
            icon.save()
        except Exception:
            icon.file.delete(save=False)
            raise
        return icon


class IconDetailSerializer(IconSerializer):
    file = serializers.ImageField(read_only=True)
