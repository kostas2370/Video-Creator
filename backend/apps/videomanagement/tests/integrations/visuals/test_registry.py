from unittest.mock import patch

from django.test import SimpleTestCase

from apps.videomanagement.integrations.visuals import (
    VIDEO_PROVIDERS,
    ImageProviderRegistry,
    bing,
    custom,
    diffusion,
    google_images,
    midjourney,
    openai_images,
    sora,
    kling,
    runway,
    gemini_video,
)


def registered_handler(prompt, directory, **kwargs):
    return "built-in.png"


def custom_handler(prompt, directory, provider_name=None, **kwargs):
    return {
        "provider": provider_name,
        "prompt": prompt,
        "directory": directory,
        **kwargs,
    }


class BuiltinImageRegistryTests(SimpleTestCase):
    def test_resolves_each_builtin_adapter(self):
        for mode, name, handler in (
            ("AI", "OPENAI", openai_images.OpenAIImageProvider.generate),
            ("AI", "sora", sora.SoraProvider.generate),
            ("AI", "kling", kling.KlingProvider.generate),
            ("AI", "runway", runway.RunwayProvider.generate),
            ("AI", "gemini-video", gemini_video.GeminiVideoProvider.generate),
            ("AI", "stable-diffusion", diffusion.StableDiffusionProvider.generate),
            ("AI", "midjourney", midjourney.MidjourneyProvider.generate),
            ("WEB", "bing", bing.BingImageProvider.generate),
            ("WEB", "google", google_images.GoogleImageProvider.generate),
        ):
            with self.subTest(provider=name):
                self.assertIs(ImageProviderRegistry.resolve(mode, name), handler)

    def test_preserves_defaults_for_blank_or_omitted_provider(self):
        for name in (None, ""):
            self.assertIs(
                ImageProviderRegistry.resolve("AI", name),
                openai_images.OpenAIImageProvider.generate,
            )
            self.assertIs(
                ImageProviderRegistry.resolve("WEB", name), bing.BingImageProvider.generate
            )

    def test_marks_the_video_adapter_for_shot_prompt_generation(self):
        self.assertEqual(VIDEO_PROVIDERS, {"sora", "kling", "runway", "gemini-video"})

    def test_provider_modules_are_resolved_at_call_time(self):
        with patch.object(openai_images.OpenAIImageProvider, "generate") as generate:
            self.assertIs(ImageProviderRegistry.resolve("AI", "OPENAI"), generate)
        self.assertIs(
            ImageProviderRegistry.resolve("AI", "OPENAI"),
            openai_images.OpenAIImageProvider.generate,
        )

    def test_unregistered_providers_use_the_mode_default_without_a_custom_fallback(
        self,
    ):
        with patch.dict(ImageProviderRegistry._fallback_providers, {}, clear=True):
            for mode, name, handler in (
                ("AI", "unconfigured", openai_images.OpenAIImageProvider.generate),
                ("WEB", "OPENAI", bing.BingImageProvider.generate),
                ("AI", "bing", openai_images.OpenAIImageProvider.generate),
            ):
                with self.subTest(mode=mode, name=name):
                    self.assertIs(ImageProviderRegistry.resolve(mode, name), handler)

    def test_custom_image_adapter_is_the_ai_fallback(self):
        handler = ImageProviderRegistry.resolve("AI", "Studio images")
        self.assertIs(handler.func, custom.CustomImageProvider.generate)
        self.assertEqual(handler.keywords, {"provider_name": "Studio images"})
        self.assertIs(
            ImageProviderRegistry.resolve("WEB", "unconfigured"), bing.BingImageProvider.generate
        )

    def test_unsupported_modes_raise_a_configuration_error(self):
        with self.assertRaises(ValueError):
            ImageProviderRegistry.resolve("invalid", "OPENAI")


class CustomImageRegistryTests(SimpleTestCase):
    def setUp(self):
        self.registry = type(
            "IsolatedImageProviderRegistry",
            (ImageProviderRegistry,),
            {},
        )

    def test_registration_returns_the_original_handler(self):
        handler = self.registry.register("studio")(registered_handler)
        self.assertIs(handler, registered_handler)
        self.assertIs(self.registry.get("studio"), registered_handler)

    def test_unknown_provider_uses_the_registered_fallback(self):
        self.registry.register_fallback()(custom_handler)
        self.assertIs(self.registry.get("studio"), custom_handler)

    def test_resolver_binds_custom_name_and_preserves_generation_arguments(self):
        self.registry.register_fallback()(custom_handler)
        generate = self.registry.resolve("AI", "My custom provider")
        result = generate(
            "a cat", "images/", user="owner", duration=8, reference="frame.png"
        )
        self.assertEqual(
            result,
            {
                "provider": "My custom provider",
                "prompt": "a cat",
                "directory": "images/",
                "user": "owner",
                "duration": 8,
                "reference": "frame.png",
            },
        )

    def test_explicit_registration_takes_priority_over_fallback(self):
        self.registry.register_fallback()(custom_handler)
        self.registry.register("studio")(registered_handler)
        self.assertIs(self.registry.resolve("AI", "studio"), registered_handler)

    def test_fallbacks_are_scoped_to_the_registered_mode(self):
        self.registry.register_fallback()(custom_handler)
        self.registry.register("bing", mode="WEB")(registered_handler)
        self.assertIs(self.registry.resolve("WEB", "studio"), registered_handler)
        with self.assertRaises(ValueError):
            self.registry.resolve("invalid", "studio")

    def test_fallbacks_can_also_be_patched_at_call_time(self):
        self.registry.register_fallback()(custom_handler)
        with patch(f"{__name__}.custom_handler") as generate:
            self.registry.resolve("AI", "studio")("a cat", "images/")
        generate.assert_called_once_with("a cat", "images/", provider_name="studio")

    def test_video_registration_updates_the_video_provider_metadata(self):
        self.registry.register("studio", output_type="VIDEO")(registered_handler)
        self.assertIn("studio", self.registry.video_providers)
        self.registry.register("studio", output_type="IMAGE")(registered_handler)
        self.assertNotIn("studio", self.registry.video_providers)

    def test_subclasses_own_their_registrations_without_manual_resets(self):
        sibling = type("Sibling", (ImageProviderRegistry,), {})
        self.registry.register("studio", output_type="VIDEO")(registered_handler)
        self.assertNotIn("studio", sibling.names())
        self.assertNotIn("studio", ImageProviderRegistry.names())

    def test_video_names_are_live_read_only_and_scoped_to_ai(self):
        names = self.registry.video_providers
        self.registry.register("studio", output_type="VIDEO")(registered_handler)
        self.registry.register("studio", mode="WEB", output_type="IMAGE")(
            registered_handler
        )
        self.assertIn("studio", names)
        self.assertTrue(self.registry.is_video("studio"))
        with self.assertRaises(AttributeError):
            names.add("unregistered")
        self.registry.register("studio", output_type="IMAGE")(registered_handler)
        self.assertNotIn("studio", names)

    def test_reference_capability_follows_current_registration_and_mode(self):
        self.registry.register("studio", supports_reference=True)(registered_handler)
        self.assertTrue(self.registry.supports_reference("studio"))
        self.assertFalse(self.registry.supports_reference("studio", mode="WEB"))
        self.registry.register("studio")(registered_handler)
        self.assertFalse(self.registry.supports_reference("studio"))

    def test_unconfigured_registry_reports_a_clear_configuration_error(self):
        with self.assertRaisesRegex(ValueError, "No visual provider configured"):
            self.registry.resolve("AI", "missing")

    def test_registration_rejects_invalid_modes_and_output_types(self):
        for kwargs in ({"mode": "invalid"}, {"output_type": "AUDIO"}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    self.registry.register("studio", **kwargs)
        with self.assertRaises(ValueError):
            self.registry.register_fallback(mode="invalid")
