from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from apps.videomanagement.integrations.base import TTSCostRequest, TTSProvider
from apps.videomanagement.integrations.tts import CustomTTSProvider, TTSRegistry


@override_settings(AI_COST_RATES={})
class TTSProviderCostTests(SimpleTestCase):
    def test_builtin_voice_calculators_do_not_generate_audio(self):
        for name in ("OPENAI", "ELEVENLABS", "SIXTYDB"):
            with self.subTest(provider=name):
                provider = TTSRegistry.provider(name)
                self.assertIsInstance(provider, TTSProvider)
                with patch.object(type(provider), "generate") as generate:
                    line = provider.calculate(TTSCostRequest("Hello κόσμε", requests=2))
                self.assertEqual(line["units"], {"characters": 11, "requests": 2})
                generate.assert_not_called()

    def test_openai_bills_characters_without_multiplying_them_by_request_count(self):
        line = TTSRegistry.provider("OPENAI").calculate(
            TTSCostRequest("Hello κόσμε", requests=3)
        )
        self.assertEqual(line["model"], "tts-1")
        self.assertEqual(line["low_usd"], "0.00016500")

    @override_settings(
        AI_COST_RATES={"tts:ELEVENLABS:eleven_multilingual_v2": {"characters": "0.01"}}
    )
    def test_elevenlabs_clone_uses_the_same_model_as_generation(self):
        provider = TTSRegistry.provider("ELEVENLABS")
        cloned = provider.calculate(
            TTSCostRequest("hello", voice=SimpleNamespace(is_cloned=True))
        )
        normal = provider.calculate(
            TTSCostRequest("hello", voice=SimpleNamespace(is_cloned=False))
        )
        self.assertEqual(cloned["model"], "eleven_multilingual_v2")
        self.assertEqual(cloned["low_usd"], "0.05000000")
        self.assertEqual(normal["model"], "eleven_multilingual_v2")
        self.assertEqual(normal["low_usd"], "0.05000000")

    @override_settings(AI_COST_RATES={"tts:Studio:": {"requests": "0.03"}})
    def test_custom_voice_costs_use_the_owned_name_and_explicit_request_count(self):
        line = CustomTTSProvider.calculate(
            TTSCostRequest("hello", requests=3, provider_name="Studio")
        )
        self.assertEqual(line["low_usd"], "0.09000000")
        self.assertEqual(line["provider"], "Studio")

    def test_custom_voice_named_openai_does_not_inherit_builtin_rates(self):
        line = CustomTTSProvider.calculate(
            TTSCostRequest("hello", provider_name="OPENAI")
        )
        self.assertEqual(line["model"], "")
        self.assertIsNone(line["low_usd"])
