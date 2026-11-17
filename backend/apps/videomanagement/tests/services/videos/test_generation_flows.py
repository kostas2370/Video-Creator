"""Queued jobs retain their contract while each input owns its generation flow."""

from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework.exceptions import ValidationError

from apps.videomanagement.services.videos import generation


class GenerationFlowRoutingTests(SimpleTestCase):
    def test_existing_jobs_route_by_input_without_duplicating_work(self):
        for recording, choices, expected in (
            (False, {"message": "An idea"}, "idea"),
            (False, {"message": "Exact words", "source_text": "Exact words"}, "text"),
            (True, {"message": "Uploaded audio"}, "audio"),
            (
                True,
                {"message": "Uploaded audio", "source_text": "Ignore supplied text"},
                "audio",
            ),
        ):
            with (
                self.subTest(recording=recording, choices=choices),
                patch.object(generation, "generate_idea_video") as idea,
                patch.object(generation, "generate_text_video") as text,
                patch.object(generation, "generate_audio_video") as audio,
            ):
                flows = {"idea": idea, "text": text, "audio": audio}
                project = SimpleNamespace(source_audio=recording)
                result = generation.generate_video(project, **choices)
                self.assertIs(result, flows[expected].return_value)
                flows[expected].assert_called_once_with(project, **choices)
                for name, flow in flows.items():
                    if name != expected:
                        flow.assert_not_called()

    def test_blank_text_cannot_fall_back_to_paid_idea_generation(self):
        with (
            self.assertRaises(ValidationError),
            patch.object(generation, "get_reply") as request,
        ):
            generation.generate_video(
                SimpleNamespace(source_audio=False), source_text="  "
            )
        request.assert_not_called()

    def test_audio_flow_requires_a_saved_recording_before_provider_work(self):
        with (
            self.assertRaises(ValidationError),
            patch.object(generation, "transcribe_audio") as request,
        ):
            generation.generate_audio_video(SimpleNamespace(source_audio=False))
        request.assert_not_called()
