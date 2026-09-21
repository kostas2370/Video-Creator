import base64
import tempfile
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings
from rest_framework.exceptions import APIException

from ...utils.image_providers import (
    openai_images,
)
from ...utils.image_providers.openai_images import generate_from_dalle


class GenerateFromDalleTests(SimpleTestCase):
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
        path = generate_from_dalle("a cat", f"{self.tmp.name}/", style="vivid")

        self.assertTrue(path.endswith(".png"))
        self.assertEqual(open(path, "rb").read(), b"a png")

    @override_settings(
        OPEN_API_KEY="key",
        IMAGE_MODEL="gpt-image-1",
        IMAGE_SIZE="1024x1024",
        IMAGE_QUALITY="high",
    )
    def test_folds_the_style_into_the_prompt(self):
        # gpt-image has no `style` argument — that was DALL-E 3 only.
        generate_from_dalle("a cat", f"{self.tmp.name}/", style="vivid", title="Cats")

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
            generate_from_dalle("a cat", f"{self.tmp.name}/", style="vivid")
