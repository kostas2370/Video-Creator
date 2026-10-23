"""Reusable fields and validation shared by API serializers."""

import math

from rest_framework import serializers


def validate_finite_numbers(values, message):
    if any(not math.isfinite(value) for value in values):
        raise serializers.ValidationError(message)


class FiniteFloat(serializers.FloatField):
    non_finite_message = None

    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        if not math.isfinite(value):
            if self.non_finite_message:
                raise serializers.ValidationError(self.non_finite_message)
            self.fail("invalid")
        return value


def validate_image_upload(
    upload,
    *,
    messages,
    max_pixels=None,
    still_only=False,
    check_order=("format", "size", "pixels", "animated"),
):
    """Validate decoded images with endpoint-specific limits and error ordering."""
    for check in check_order:
        if check == "size":
            invalid = upload.size > 10 * 1024 * 1024
        elif check == "format":
            invalid = upload.image.format not in ("PNG", "JPEG", "WEBP")
        elif check == "pixels":
            invalid = max_pixels is not None and (
                upload.image.width * upload.image.height > max_pixels
            )
        elif check == "animated":
            invalid = still_only and getattr(upload.image, "is_animated", False)
        else:
            raise ValueError(f"Unknown image validation check: {check}")
        if invalid:
            raise serializers.ValidationError(messages[check])
    return upload
