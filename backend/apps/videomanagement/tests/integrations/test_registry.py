"""Voice and visual registries share lookup rules without sharing registrations."""

from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework.exceptions import ValidationError

from apps.apikeysmanagement.serializers import (
    UserCustomTTSProviderSerializer,
    UserCustomVisualProviderSerializer,
)
from apps.videomanagement.integrations.registry import ProviderRegistry
from apps.videomanagement.integrations.tts import TTSRegistry
from apps.videomanagement.integrations.visuals.registry import ImageProviderRegistry


def handler(*args, **kwargs):
    return "registered"


def fallback(*args, **kwargs):
    return "fallback"


class ProviderRegistryTests(SimpleTestCase):
    def setUp(self):
        self.registry = type("IsolatedRegistry", (ProviderRegistry,), {})

    def test_no_handler_or_fallback_returns_none(self):
        self.assertIsNone(self.registry.get("unknown"))

    def test_explicit_handler_wins_and_fallback_is_late_bound(self):
        self.registry.register_fallback()(fallback)
        self.registry.register("known")(handler)
        with patch(f"{__name__}.handler") as replacement:
            self.assertIs(self.registry.get("known"), replacement)
        with patch(f"{__name__}.fallback") as replacement:
            self.assertIs(self.registry.get("unknown"), replacement)

    def test_voice_handlers_can_be_registered_outside_tts_module(self):
        registry = type("IsolatedTTSRegistry", (TTSRegistry,), {})
        registry.register("external")(handler)
        self.assertIs(registry.get("external"), handler)
        self.assertNotIn("external", TTSRegistry.names())

    def test_capabilities_cannot_be_mutated_through_registration(self):
        self.registry.register("known", output_type="VIDEO")(handler)
        with self.assertRaises(TypeError):
            self.registry.registration("known").capabilities["output_type"] = "IMAGE"

    def test_voice_and_visual_fallbacks_are_independent(self):
        voice = type("Voices", (TTSRegistry,), {})
        visual = type("Visuals", (ImageProviderRegistry,), {})
        voice.register_fallback()(fallback)
        visual.register_fallback()(handler)
        self.assertIs(voice.get("custom"), fallback)
        self.assertIs(visual.get("custom"), handler)

    def test_custom_names_are_reserved_from_current_voice_and_visual_registrations(
        self,
    ):
        for registry, serializer, mode in (
            (TTSRegistry, UserCustomTTSProviderSerializer, "default"),
            (ImageProviderRegistry, UserCustomVisualProviderSerializer, "AI"),
        ):
            with (
                self.subTest(registry=registry.__name__),
                patch.dict(
                    registry._providers,
                    {mode: {}},
                    clear=True,
                ),
            ):
                registry.register("Future-provider")(handler)
                with self.assertRaises(ValidationError):
                    serializer().validate_name("FUTURE-PROVIDER")
