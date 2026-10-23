"""Regression coverage for limits shared by otherwise distinct API contracts."""

from types import SimpleNamespace

from django.test import SimpleTestCase
from rest_framework.exceptions import ValidationError

from ...serializers.caption_styles import CaptionStyleSerializer
from ...serializers.caption_words import CaptionWordSerializer
from ...serializers.covers import CoverSerializer
from ...serializers.fields import FiniteFloat
from ...serializers.overlays import OverlaySerializer, SceneOverlaysSerializer


class SharedValidationTests(SimpleTestCase):
    def image(self, *, size=1024, pixels=100, format="PNG", animated=False):
        return SimpleNamespace(
            size=size,
            image=SimpleNamespace(
                width=pixels, height=1, format=format, is_animated=animated
            ),
        )

    def test_cover_and_logo_keep_different_pixel_limits(self):
        upload = self.image(pixels=18_000_000)
        self.assertIs(CoverSerializer().validate_image(upload), upload)
        with self.assertRaisesMessage(ValidationError, "16 million pixels"):
            SceneOverlaysSerializer().validate_overlay_logo(upload)

    def test_only_logos_require_a_still_image(self):
        upload = self.image(animated=True)
        self.assertIs(CoverSerializer().validate_image(upload), upload)
        with self.assertRaisesMessage(ValidationError, "still image"):
            SceneOverlaysSerializer().validate_overlay_logo(upload)

    def test_uploads_keep_their_error_priority(self):
        upload = self.image(size=11 * 1024 * 1024, format="GIF")
        with self.assertRaisesMessage(
            ValidationError, "Choose a PNG, JPEG, or WebP image."
        ):
            CoverSerializer().validate_image(upload)
        with self.assertRaisesMessage(
            ValidationError, "Use a logo smaller than 10 MB."
        ):
            SceneOverlaysSerializer().validate_overlay_logo(upload)

    def test_image_size_boundary_is_unchanged(self):
        upload = self.image(size=10 * 1024 * 1024)
        self.assertIs(CoverSerializer().validate_image(upload), upload)
        upload.size += 1
        with self.assertRaisesMessage(ValidationError, "smaller than 10 MB"):
            CoverSerializer().validate_image(upload)

    def test_all_shared_numeric_paths_reject_nonfinite_values(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    FiniteFloat().run_validation(value)
                style = CaptionStyleSerializer(data={"font_size": value})
                self.assertFalse(style.is_valid())
                word = CaptionWordSerializer(
                    data={"text": "Hello", "start": 0, "end": value}
                )
                self.assertFalse(word.is_valid())
                overlay = OverlaySerializer(
                    data={"kind": "title", "text": "Hello", "start": value}
                )
                self.assertFalse(overlay.is_valid())
