from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework.exceptions import APIException

from apps.videomanagement.integrations.base import ImageCostRequest
from apps.videomanagement.integrations.visuals.sora import SoraProvider


class RetiredSoraTests(SimpleTestCase):
    def test_saved_sora_projects_fail_without_calling_any_provider(self):
        with patch("openai.OpenAI") as client:
            with self.assertRaisesRegex(APIException, "Sora is no longer available"):
                SoraProvider.generate(prompt="cat", dir_name="/tmp/")
        client.assert_not_called()

    def test_estimates_explain_that_another_provider_is_required(self):
        line = SoraProvider.calculate(ImageCostRequest())
        self.assertIn("Sora is no longer available", line["note"])
        self.assertIsNone(line["low_usd"])
