from importlib import import_module
from unittest.mock import patch
from types import SimpleNamespace

from django.apps import apps
from django.db import connection
from django.test import TestCase
from model_bakery import baker

from apps.videomanagement.integrations.llm import get_reply
from apps.videomanagement.models import TemplatePrompt, Video
from video_creator.model_catalog import SCRIPT_MODEL_REPLACEMENTS


class ModelUpdateTests(TestCase):
    def test_upgrades_saved_templates_and_retry_parameters_without_rewriting_history(
        self,
    ):
        template = baker.make(TemplatePrompt, gpt_model="gemini-1.5-pro")
        video = baker.make(
            Video,
            settings={
                "generation_params": {
                    "gpt_model": "gemini-1.5-flash",
                    "message": "cat",
                },
                "other": True,
            },
            gpt_answer={"title": "Original script"},
        )
        migration = import_module(
            "apps.videomanagement.migrations.0053_replace_retired_script_models"
        )
        migration.replace_saved_models(apps, SimpleNamespace(connection=connection))
        template.refresh_from_db()
        video.refresh_from_db()
        self.assertEqual(template.gpt_model, "gemini-4-argon")
        self.assertEqual(
            video.settings,
            {
                "generation_params": {
                    "gpt_model": "gemini-3.8-flash",
                    "message": "cat",
                },
                "other": True,
            },
        )
        self.assertEqual(video.gpt_answer, {"title": "Original script"})

    def test_queued_requests_with_old_ids_use_the_same_provider_replacement(self):
        for old, new in SCRIPT_MODEL_REPLACEMENTS.items():
            function = "claude_call" if old.startswith("claude") else "gemini_call"
            with (
                self.subTest(model=old),
                patch("apps.videomanagement.integrations.llm." + function) as call,
            ):
                get_reply("prompt", gpt_model=old, reply_format="text")
            call.assert_called_once_with("prompt", new, user=None)
