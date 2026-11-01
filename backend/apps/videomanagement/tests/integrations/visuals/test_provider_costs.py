from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from apps.videomanagement.integrations.base import ImageCostRequest, ImageProvider
from apps.videomanagement.integrations.visuals import ImageProviderRegistry
from apps.videomanagement.integrations.visuals.custom import CustomImageProvider
from apps.videomanagement.integrations.visuals.openai_images import OpenAIImageProvider


@override_settings(IMAGE_MODEL="gpt-image-2", IMAGE_QUALITY="high", AI_COST_RATES={})
class ImageProviderCostTests(SimpleTestCase):
    @override_settings(SILENT_SCENE_SECONDS=30)
    def test_video_calculators_use_generation_duration_rounding_and_clamps(self):
        for name, provider_name, expected in (
            ("runway", "RUNWAY", 26),
            ("kling", "FAL", 37),
            ("gemini-video", "GEMINI", 27),
        ):
            with self.subTest(provider=name):
                provider = ImageProviderRegistry.provider(name, "AI")
                self.assertIsInstance(provider, ImageProvider)
                with patch.object(type(provider), "generate") as generate:
                    line = provider.calculate(
                        ImageCostRequest(count=4, durations=(0.2, 3.1, 100, None))
                    )
                self.assertEqual(line["provider"], provider_name)
                self.assertEqual(line["units"], {"seconds": expected, "requests": 4})
                generate.assert_not_called()

    def test_runway_uses_its_known_per_second_rate(self):
        line = ImageProviderRegistry.provider("runway", "AI").calculate(
            ImageCostRequest(count=2, durations=(1, 3.1))
        )
        self.assertEqual(line["low_usd"], "0.72000000")

    def test_image_registrations_expose_class_calculators_without_generating_media(
        self,
    ):
        for mode, names in (
            ("AI", ("OPENAI", "midjourney", "stable-diffusion")),
            ("WEB", ("bing", "google")),
        ):
            for name in names:
                with self.subTest(provider=name):
                    provider = ImageProviderRegistry.provider(name, mode)
                    self.assertIsInstance(provider, ImageProvider)
                    with patch.object(type(provider), "generate") as generate:
                        line = provider.calculate(ImageCostRequest(count=3))
                    self.assertEqual(line["units"], {"images": 3, "requests": 3})
                    generate.assert_not_called()

    def test_openai_prices_standard_and_economy_without_changing_settings(self):
        standard = OpenAIImageProvider.calculate(ImageCostRequest(count=2))
        economy = OpenAIImageProvider.calculate(
            ImageCostRequest(count=2, generation_mode="ECONOMY")
        )
        self.assertEqual(
            (standard["low_usd"], standard["high_usd"]), ("0.33000000", "0.42200000")
        )
        self.assertEqual(
            (economy["low_usd"], economy["high_usd"]), ("0.08200000", "0.10600000")
        )
        self.assertEqual(
            OpenAIImageProvider.calculate(ImageCostRequest(count=2)), standard
        )

    @override_settings(IMAGE_QUALITY="low")
    def test_economy_preserves_a_low_quality_installation(self):
        line = OpenAIImageProvider.calculate(
            ImageCostRequest(generation_mode="ECONOMY")
        )
        self.assertEqual(line["low_usd"], "0.00500000")

    @override_settings(AI_COST_RATES={"images:STABLE_DIFFUSION:": {"images": "0.02"}})
    def test_builtin_calculators_use_the_recorded_provider_identifier(self):
        line = ImageProviderRegistry.provider("stable-diffusion", "AI").calculate(
            ImageCostRequest(count=3)
        )
        self.assertEqual(line["provider"], "STABLE_DIFFUSION")
        self.assertEqual(line["low_usd"], "0.06000000")

    def test_custom_names_do_not_inherit_openai_model_prices(self):
        line = CustomImageProvider.calculate(ImageCostRequest(provider_name="OPENAI"))
        self.assertEqual(line["model"], "")
        self.assertIsNone(line["low_usd"])

    @override_settings(
        AI_COST_RATES={
            "images:Studio A:": {"images": "0.03"},
            "video:Studio B:": {"requests": "0.4"},
        }
    )
    def test_custom_calculations_keep_name_output_type_and_units_per_request(self):
        provider = CustomImageProvider()
        image = provider.calculate(ImageCostRequest(count=2, provider_name="Studio A"))
        video = provider.calculate(
            ImageCostRequest(count=3, provider_name="Studio B", output_type="VIDEO")
        )
        self.assertEqual(image["low_usd"], "0.06000000")
        self.assertEqual(video["low_usd"], "1.20000000")
        self.assertEqual(video["units"], {"requests": 3})
