from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.videomanagement.services.scenes.timeline import scene_segment
from apps.videomanagement.utils.prompt_utils import build_script_prompt
from apps.videomanagement.utils.video_audio import audio_mode, audio_direction


class VideoAudioTests(SimpleTestCase):
    def test_no_narration_allows_dialogue_in_the_script_and_generation_direction(self):
        prompt = build_script_prompt(
            "A conversation", image_mode="AI", video=True, narration=False
        )
        self.assertIn("Allow brief, natural character dialogue", prompt)
        self.assertNotIn("write no spoken lines", prompt)
        self.assertEqual(audio_mode({"narration": False}), "DIALOGUE")
        self.assertNotIn(
            "No character speech", audio_direction(audio_mode({"narration": False}))
        )

    def test_narration_defaults_to_ambient_with_explicit_dialogue_and_silent_overrides(
        self,
    ):
        self.assertEqual(audio_mode({"narration": True}), "AMBIENT")
        self.assertIn(
            "No character speech", audio_direction(audio_mode({"narration": True}))
        )
        self.assertEqual(
            audio_mode({"narration": True, "video_audio_mode": "DIALOGUE"}), "DIALOGUE"
        )
        self.assertIn(
            "silent clip",
            audio_direction(
                audio_mode({"narration": False, "video_audio_mode": "SILENT"})
            ),
        )

    def test_global_clip_mute_is_honored_by_preview_and_render_timeline(self):
        project = SimpleNamespace(
            settings={"narration": False, "video_audio_enabled": False}
        )
        image = SimpleNamespace(file=SimpleNamespace(name="clip.mp4"), with_audio=True)
        line = SimpleNamespace(
            video=project,
            scene_images=SimpleNamespace(all=lambda: [image]),
            voiceover=None,
            file=None,
            audio_settings={},
            is_last=False,
            pause_after=0,
            transition_after="CUT",
            transition_duration=None,
        )
        with (
            patch(
                "apps.videomanagement.services.scenes.timeline.file_timing",
                return_value={"duration": 8, "audio_duration": 8},
            ),
            patch(
                "apps.videomanagement.utils.timing.file_timing",
                return_value={"duration": 8, "audio_duration": 8},
            ),
        ):
            self.assertFalse(scene_segment(line, 1, 0, project.settings).clip_audio)
            project.settings["video_audio_enabled"] = True
            self.assertTrue(scene_segment(line, 1, 0, project.settings).clip_audio)
