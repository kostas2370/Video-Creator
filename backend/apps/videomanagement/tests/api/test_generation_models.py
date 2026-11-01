from django.conf import settings
from django.urls import reverse
from django.test import override_settings

from .base import ApiTestCase


class GenerationModelsTests(ApiTestCase):
    def test_returns_the_same_model_dictionary_and_default_used_by_validation(self):
        response = self.client.get(reverse("generation_models"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data,
            {
                "script_models": settings.SCRIPT_MODELS,
                "default_script_model": settings.DEFAULT_GPT_MODEL,
            },
        )
        self.assertEqual(
            settings.ACCEPTED_MODELS,
            [
                model
                for models in response.data["script_models"].values()
                for model in models
            ],
        )

    @override_settings(
        SCRIPT_MODELS={"Studio": ["a-new-model"]}, DEFAULT_GPT_MODEL="a-new-model"
    )
    def test_configuration_changes_are_visible_without_frontend_changes(self):
        self.assertEqual(
            self.client.get(reverse("generation_models")).data,
            {
                "script_models": {"Studio": ["a-new-model"]},
                "default_script_model": "a-new-model",
            },
        )

    def test_requires_authentication(self):
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get(reverse("generation_models")).status_code, 401)
