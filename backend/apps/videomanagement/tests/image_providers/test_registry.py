from unittest.mock import patch

from django.test import SimpleTestCase

from ...utils.image_providers import (
    ImageProviderRegistry,
    VIDEO_PROVIDERS,
    bing,
    custom,
    diffusion,
    google_images,
    midjourney,
    openai_images,
    sora,
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
            ("AI", "DALL-E", openai_images.generate_from_dalle),
            ("AI", "sora", sora.generate_from_sora),
            ("AI", "stable-diffusion", diffusion.generate_from_diffusion),
            ("AI", "midjourney", midjourney.generate_from_midjourney),
            ("WEB", "bing", bing.download_image),
            ("WEB", "google", google_images.download_image_from_google),
        ):
            with self.subTest(provider=name):
                self.assertIs(ImageProviderRegistry.resolve(mode, name), handler)

    def test_preserves_defaults_for_blank_or_omitted_provider(self):
        for name in (None, ""):
            self.assertIs(ImageProviderRegistry.resolve("AI", name), openai_images.generate_from_dalle)
            self.assertIs(ImageProviderRegistry.resolve("WEB", name), bing.download_image)

    def test_marks_the_video_adapter_for_shot_prompt_generation(self):
        self.assertEqual(VIDEO_PROVIDERS, {"sora"})

    def test_provider_modules_are_resolved_at_call_time(self):
        with patch.object(openai_images, "generate_from_dalle") as generate:
            self.assertIs(ImageProviderRegistry.resolve("AI", "DALL-E"), generate)
        self.assertIs(ImageProviderRegistry.resolve("AI", "DALL-E"), openai_images.generate_from_dalle)

    def test_unregistered_providers_use_the_mode_default_without_a_custom_fallback(
        self,
    ):
        with patch.dict(ImageProviderRegistry._fallback_providers, {}, clear=True):
            for mode, name, handler in (
                ("AI", "unconfigured", openai_images.generate_from_dalle),
                ("WEB", "DALL-E", bing.download_image),
                ("AI", "bing", openai_images.generate_from_dalle),
            ):
                with self.subTest(mode=mode, name=name):
                    self.assertIs(ImageProviderRegistry.resolve(mode, name), handler)

    def test_custom_image_adapter_is_the_ai_fallback(self):
        handler = ImageProviderRegistry.resolve("AI", "Studio images")
        self.assertIs(handler.func, custom.generate_from_custom_provider)
        self.assertEqual(handler.keywords, {"provider_name": "Studio images"})
        self.assertIs(ImageProviderRegistry.resolve("WEB", "unconfigured"), bing.download_image)

    def test_unsupported_modes_raise_a_configuration_error(self):
        with self.assertRaises(ValueError):
            ImageProviderRegistry.resolve("invalid", "DALL-E")


class CustomImageRegistryTests(SimpleTestCase):
    def setUp(self):
        self.registry = type(
            "IsolatedImageProviderRegistry",
            (ImageProviderRegistry,),
            {"_providers": {}, "_fallback_providers": {}, "video_providers": set()},
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

    def test_registration_rejects_invalid_modes_and_output_types(self):
        for kwargs in ({"mode": "invalid"}, {"output_type": "AUDIO"}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    self.registry.register("studio", **kwargs)
        with self.assertRaises(ValueError):
            self.registry.register_fallback(mode="invalid")
