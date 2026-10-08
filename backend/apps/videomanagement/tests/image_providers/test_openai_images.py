import base64
import tempfile
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings
from rest_framework.exceptions import APIException

from ...utils.image_providers import (
    openai_images,
)
from ...utils.image_providers.openai_images import generate_openai_image


class GenerateOpenAIImageTests(SimpleTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.client = MagicMock()
        self.client.images.generate.return_value.data = [
            MagicMock(b64_json=base64.b64encode(b"a png").decode())
        ]
        patcher = patch.object(openai_images, "OpenAI", return_value=self.client)
        patcher.start()
        self.addCleanup(patcher.stop)

    @override_settings(
        OPEN_API_KEY="key",
        IMAGE_MODEL="gpt-image-1",
        IMAGE_SIZE="1024x1024",
        IMAGE_QUALITY="high",
    )
    def test_decodes_the_image_to_a_png(self):
        path = generate_openai_image("a cat", f"{self.tmp.name}/", style="vivid")

        self.assertTrue(path.endswith(".png"))
        self.assertEqual(open(path, "rb").read(), b"a png")

    @override_settings(
        OPEN_API_KEY="key",
        IMAGE_MODEL="gpt-image-1",
        IMAGE_SIZE="1024x1024",
        IMAGE_QUALITY="high",
    )
    def test_folds_the_style_into_the_prompt(self):
        generate_openai_image("a cat", f"{self.tmp.name}/", style="vivid", title="Cats")

        kwargs = self.client.images.generate.call_args.kwargs
        self.assertIn("Style: vivid", kwargs["prompt"])
        self.assertNotIn("style", kwargs)

    @override_settings(
        OPEN_API_KEY="key",
        IMAGE_MODEL="gpt-image-1",
        IMAGE_SIZE="1024x1024",
        IMAGE_QUALITY="high",
    )
    def test_raises_when_the_model_returns_no_image(self):
        self.client.images.generate.return_value.data = []

        with self.assertRaises(APIException):
            generate_openai_image("a cat", f"{self.tmp.name}/", style="vivid")

    @override_settings(OPEN_API_KEY="key", IMAGE_MODEL="gpt-image-2")
    def test_uses_reference_edits_and_keeps_the_configured_model(self):
        self.client.images.edit.return_value.data = [
            MagicMock(b64_json=base64.b64encode(b"reference result").decode())
        ]
        with tempfile.NamedTemporaryFile(suffix=".png") as anchor:
            path = generate_openai_image(
                "cat running", f"{self.tmp.name}/", style="vivid", reference=anchor.name
            )
        self.client.images.generate.assert_not_called()
        kwargs = self.client.images.edit.call_args.kwargs
        self.assertEqual(kwargs["model"], "gpt-image-2")
        self.assertNotIn("input_fidelity", kwargs)
        self.assertIn("Preserve recurring characters", kwargs["prompt"])
        with open(path, "rb") as result:
            self.assertEqual(result.read(), b"reference result")

    @override_settings(OPEN_API_KEY="key", IMAGE_MODEL="gpt-image-1")
    def test_older_supported_models_request_high_input_fidelity(self):
        self.client.images.edit.return_value.data = (
            self.client.images.generate.return_value.data
        )
        with tempfile.NamedTemporaryFile(suffix=".png") as anchor:
            generate_openai_image(
                "cat", f"{self.tmp.name}/", style="", reference=anchor.name
            )
        self.assertEqual(
            self.client.images.edit.call_args.kwargs["input_fidelity"], "high"
        )

    @override_settings(OPEN_API_KEY="key")
    def test_missing_reference_generates_a_fresh_image(self):
        generate_openai_image(
            "cat", f"{self.tmp.name}/", style="", reference="/missing.png"
        )
        self.client.images.generate.assert_called_once()
        self.client.images.edit.assert_not_called()

    @override_settings(OPEN_API_KEY="key")
    def test_failed_reference_edit_is_not_silently_replaced_by_unanchored_generation(
        self,
    ):
        self.client.images.edit.side_effect = RuntimeError("edit failed")
        with (
            tempfile.NamedTemporaryFile(suffix=".png") as anchor,
            self.assertRaises(RuntimeError),
        ):
            generate_openai_image(
                "cat", f"{self.tmp.name}/", style="", reference=anchor.name
            )
        self.client.images.generate.assert_not_called()
