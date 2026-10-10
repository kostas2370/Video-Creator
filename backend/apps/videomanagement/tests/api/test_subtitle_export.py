import tempfile
import wave
from pathlib import Path

from django.test import override_settings
from django.urls import reverse

from apps.usermanagement.baker_recipes import user
from ...baker_recipes import intro, scene, scene_image
from .base import ApiTestCase


class SubtitleExportTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        override = override_settings(MEDIA_ROOT=self.directory.name)
        override.enable()
        self.addCleanup(override.disable)
        with wave.open(str(Path(self.directory.name, "speech.wav")), "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(8000)
            audio.writeframes(b"\0\0" * 16000)
        self.video = self.video_for(title="Ελληνικά", status="READY", settings={"narration": True, "subtitles": False})
        self.first = scene.make(video=self.video, file="speech.wav", text="Γεια σου κόσμε.", pause_after=0.75)
        self.second = scene.make(video=self.video, file="speech.wav", text="Second scene.")
        self.url = reverse("video-subtitles", args=[self.video.pk])

    def test_export_uses_recorded_audio_and_skips_pauses_without_charging(self):
        self.user.generation_limit_for_ai = 0
        self.user.save()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("application/x-subrip", response["Content-Type"])
        self.assertIn("attachment;", response["Content-Disposition"])
        self.assertIn("filename*=utf-8", response["Content-Disposition"])
        text = response.content.decode("utf-8")
        self.assertEqual(text, "1\n00:00:00,000 --> 00:00:02,000\nΓεια σου κόσμε.\n\n2\n00:00:02,750 --> 00:00:04,750\nSecond scene.\n")
        self.user.refresh_from_db()
        self.assertEqual(self.user.generation_limit_for_ai, 0)

    def test_reordering_changes_the_export_and_missing_narration_leaves_a_gap(self):
        self.first.position = 3
        self.first.save()
        self.second.position = 1
        self.second.save()
        self.first.position = 2
        self.first.file = None
        self.first.save()
        third = scene.make(video=self.video, file="speech.wav", text="Third scene.")
        text = self.client.get(self.url).content.decode("utf-8")
        self.assertIn("00:00:00,000 --> 00:00:02,000\nSecond scene.", text)
        self.assertIn("00:00:03,750 --> 00:00:05,750\nThird scene.", text)
        self.assertNotIn("Γεια", text)

    def test_intro_and_existing_ending_hold_offset_later_cues(self):
        self.video.intro = intro.make(file="speech.wav", created_by=self.user)
        self.video.save()
        self.first.is_last = True
        self.first.save()
        scene_image.make(scene=self.first)
        text = self.client.get(self.url).content.decode("utf-8")
        self.assertIn("00:00:02,000 --> 00:00:04,000\nΓεια σου κόσμε.", text)
        self.assertIn("00:00:06,750 --> 00:00:08,750\nSecond scene.", text)

    def test_export_is_private_and_blocked_during_processing(self):
        for state in ("GENERATION", "RENDERING", "REVIEW"):
            self.video.status = state
            self.video.save()
            self.assertEqual(self.client.get(self.url).status_code, 409)
        foreign = self.video_for(owner=user.make())
        self.assertEqual(self.client.get(reverse("video-subtitles", args=[foreign.pk])).status_code, 404)
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get(self.url).status_code, 401)

    def test_export_reports_unavailable_narration_and_intro(self):
        self.video.settings = {"narration": False}
        self.video.save()
        self.assertEqual(self.client.get(self.url).status_code, 400)
        self.video.settings = {"narration": True}
        self.video.intro = intro.make(file="missing.mp4", created_by=self.user)
        self.video.save()
        self.assertEqual(self.client.get(self.url).status_code, 400)
        self.video.intro = None
        self.video.save()
        self.video.scenes.update(file=None)
        self.assertEqual(self.client.get(self.url).status_code, 400)
