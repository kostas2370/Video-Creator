from django.test import SimpleTestCase, override_settings

from apps.videomanagement.utils.generation_quality import image_quality_for


class GenerationQualityTests(SimpleTestCase):
    @override_settings(IMAGE_QUALITY="high")
    def test_standard_keeps_configured_quality_and_economy_uses_medium(self):
        self.assertEqual(image_quality_for(), "high")
        self.assertEqual(image_quality_for("STANDARD"), "high")
        self.assertEqual(image_quality_for("ECONOMY"), "medium")
        self.assertEqual(image_quality_for(), "high")

    @override_settings(IMAGE_QUALITY="low")
    def test_economy_never_increases_low_quality(self):
        self.assertEqual(image_quality_for("ECONOMY"), "low")

    @override_settings(IMAGE_QUALITY="auto")
    def test_standard_preserves_automatic_quality(self):
        self.assertEqual(image_quality_for(), "auto")
        self.assertEqual(image_quality_for("ECONOMY"), "medium")
