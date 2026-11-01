from unittest.mock import patch

from django.test import SimpleTestCase

from apps.videomanagement.integrations.base import (
    ImageCostRequest,
    ImageProvider,
    TTSCostRequest,
    TTSProvider,
)
from apps.videomanagement.integrations.registry import ProviderRegistry


class ExampleImageProvider(ImageProvider):
    def generate(self, prompt, **kwargs):
        return prompt

    def calculate(self, request):
        return {"images": request.count}


class IncompleteTTSProvider(TTSProvider):
    def generate(self, text, **kwargs):
        return text


class ProviderInterfaceTests(SimpleTestCase):
    def setUp(self):
        self.registry = type("IsolatedRegistry", (ProviderRegistry,), {})

    def test_both_interfaces_require_generation_and_calculation(self):
        for provider in (ImageProvider, TTSProvider, IncompleteTTSProvider):
            with self.subTest(provider=provider), self.assertRaises(TypeError):
                provider()

    def test_class_registration_exposes_generation_and_calculation_separately(self):
        self.registry.register("example")(ExampleImageProvider)
        self.assertEqual(self.registry.get("example")("fox"), "fox")
        provider = self.registry.provider("example")
        self.assertIsInstance(provider, ImageProvider)
        with patch.object(ExampleImageProvider, "generate") as generate:
            self.assertEqual(
                provider.calculate(ImageCostRequest(count=3)), {"images": 3}
            )
        generate.assert_not_called()

    def test_class_generation_remains_late_bound(self):
        self.registry.register("example")(ExampleImageProvider)
        with patch.object(ExampleImageProvider, "generate", return_value="new"):
            self.assertEqual(self.registry.get("example")("fox"), "new")

    def test_class_fallback_is_available_without_sharing_registry_state(self):
        self.registry.register_fallback()(ExampleImageProvider)
        self.assertIsInstance(self.registry.provider("custom"), ImageProvider)
        self.assertIsNone(ProviderRegistry.provider("custom"))

    def test_cost_requests_preserve_distinct_image_and_voice_units(self):
        self.assertEqual(ImageCostRequest(count=2).count, 2)
        voice = TTSCostRequest(text="Hello κόσμε", requests=2)
        self.assertEqual(voice.text, "Hello κόσμε")
        self.assertEqual(voice.requests, 2)
