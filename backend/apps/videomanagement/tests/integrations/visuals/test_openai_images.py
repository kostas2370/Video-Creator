import base64
import tempfile
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from rest_framework.exceptions import APIException

from apps.videomanagement.integrations.visuals import openai_images
from apps.videomanagement.integrations.visuals.openai_images import (
    generate_openai_image,
)


class GenerateOpenAIImageTests(TestCase):
    @override_settings(IMAGE_QUALITY="high", IMAGE_MODEL="gpt-image-2")
    def test_economy_changes_only_the_explicit_request_quality(self):
        generate_openai_image("cat", f"{self.tmp.name}/", style="natural", generation_mode="ECONOMY")
        self.assertEqual(self.client.images.generate.call_args.kwargs["quality"], "medium")
        generate_openai_image("cat", f"{self.tmp.name}/", style="natural")
        self.assertEqual(self.client.images.generate.call_args.kwargs["quality"], "high")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        settings_override = override_settings(MEDIA_ROOT=self.tmp.name)
        settings_override.enable()
        self.addCleanup(settings_override.disable)
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
        self.assertTrue(openai_images.MediaAsset.objects.filter(kind="IMAGE").exists())
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

    @override_settings(
        OPEN_API_KEY="key", IMAGE_MODEL="gpt-image-2", IMAGE_SIZE="1792x1024"
    )
    def test_scene_generation_uses_exact_project_aspect_ratios(self):
        for frame, expected in (
            ("PORTRAIT", "864x1536"),
            ("LANDSCAPE", "1536x864"),
            ("SQUARE", "1024x1024"),
        ):
            with self.subTest(frame=frame):
                generate_openai_image(
                    "a cat", f"{self.tmp.name}/", style="", video_format=frame
                )
                self.assertEqual(
                    self.client.images.generate.call_args.kwargs["size"], expected
                )

    @override_settings(
        OPEN_API_KEY="key", IMAGE_MODEL="gpt-image-2", IMAGE_SIZE="1792x1024"
    )
    def test_reference_edits_also_follow_the_project_frame(self):
        self.client.images.edit.return_value.data = (
            self.client.images.generate.return_value.data
        )
        with tempfile.NamedTemporaryFile(suffix=".png") as anchor:
            for frame, expected in (
                ("PORTRAIT", "864x1536"),
                ("LANDSCAPE", "1536x864"),
                ("SQUARE", "1024x1024"),
            ):
                with self.subTest(frame=frame):
                    generate_openai_image(
                        "a cat",
                        f"{self.tmp.name}/",
                        style="",
                        reference=anchor.name,
                        video_format=frame,
                    )
                    self.assertEqual(
                        self.client.images.edit.call_args.kwargs["size"], expected
                    )
        self.client.images.generate.assert_not_called()

    @override_settings(OPEN_API_KEY="key", IMAGE_SIZE="1792x1024")
    def test_older_models_use_supported_sizes_in_both_request_paths(self):
        self.client.images.edit.return_value.data = (
            self.client.images.generate.return_value.data
        )
        for model in ("gpt-image-1", "gpt-image-1.5", "gpt-image-1-mini"):
            with (
                override_settings(IMAGE_MODEL=model),
                tempfile.NamedTemporaryFile(suffix=".png") as anchor,
            ):
                for frame, expected in (
                    ("PORTRAIT", "1024x1536"),
                    ("LANDSCAPE", "1536x1024"),
                    ("SQUARE", "1024x1024"),
                ):
                    with self.subTest(model=model, frame=frame):
                        generate_openai_image(
                            "a cat", f"{self.tmp.name}/", style="", video_format=frame
                        )
                        self.assertEqual(
                            self.client.images.generate.call_args.kwargs["size"],
                            expected,
                        )
                        generate_openai_image(
                            "a cat",
                            f"{self.tmp.name}/",
                            style="",
                            reference=anchor.name,
                            video_format=frame,
                        )
                        self.assertEqual(
                            self.client.images.edit.call_args.kwargs["size"], expected
                        )

    @override_settings(OPEN_API_KEY="key", IMAGE_MODEL="gpt-image-2-2026-04-21")
    def test_pinned_model_snapshots_keep_exact_portrait_sizing(self):
        generate_openai_image(
            "a cat", f"{self.tmp.name}/", style="", video_format="PORTRAIT"
        )
        self.assertEqual(
            self.client.images.generate.call_args.kwargs["size"], "864x1536"
        )

    @override_settings(
        OPEN_API_KEY="key", IMAGE_MODEL="gpt-image-2", IMAGE_SIZE="1024x1024"
    )
    def test_standalone_and_unknown_format_requests_keep_configured_size(self):
        for frame in (None, "UNKNOWN"):
            with self.subTest(frame=frame):
                generate_openai_image(
                    "a cover", f"{self.tmp.name}/", style="", video_format=frame
                )
                self.assertEqual(
                    self.client.images.generate.call_args.kwargs["size"], "1024x1024"
                )
