import tempfile
import wave
from pathlib import Path
from unittest.mock import patch

from django.test import override_settings
from django.urls import reverse

from apps.usermanagement.baker_recipes import user
from apps.videomanagement.services.captions.alignment import (
    align_scene_narration,
    narration_identity,
)
from apps.videomanagement.services.captions.subtitles import export_subtitles
from apps.videomanagement.services.videos.preview import preview_timeline

from ...baker_recipes import scene
from ...utils.composer.render import write_captions
from .base import ApiTestCase


class SceneCaptionEditingTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        override = override_settings(MEDIA_ROOT=directory.name)
        override.enable()
        self.addCleanup(override.disable)
        self.audio = Path(directory.name, "voice.wav")
        with wave.open(str(self.audio), "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(8000)
            audio.writeframes(b"\0\0" * 32000)
        self.video = self.video_for(settings={"narration": True, "subtitles": True, "caption_style": "TIKTOK"})
        self.scene = scene.make(video=self.video, file=str(self.audio), text="Hello world.")
        self.url = reverse("scene-captions", args=[self.scene.pk])
        self.words = [{"text": "Corrected", "start": 0.5, "end": 1.2}, {"text": "caption.", "start": 1.5, "end": 2.4}]

    def save(self, words=None, revision=None):
        if revision is None:
            revision = self.client.get(self.url).data["revision"]
        return self.client.patch(self.url, {"words": self.words if words is None else words, "revision": revision}, format="json")

    def test_corrections_reach_preview_render_and_srt_without_changing_narration(self):
        response = self.save()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["timing"], "edited")
        self.scene.refresh_from_db()
        self.assertEqual(self.scene.text, "Hello world.")
        self.assertEqual(self.scene.file.name, str(self.audio))
        timeline = preview_timeline(self.video)
        self.assertEqual(timeline.captions[0].start, 0.5)
        self.assertEqual(timeline.captions[0].text, "Corrected caption.")
        self.assertEqual(timeline.captions[1].active_word, 1)
        ass = self.audio.with_suffix(".ass")
        write_captions(ass, timeline.segments, (1080, 1920))
        self.assertIn("CORRECTED", ass.read_text())
        self.assertIn("0:00:00.50,0:00:01.50", ass.read_text())
        self.assertIn("Corrected caption.", export_subtitles(self.video))
        self.assertEqual(self.client.get(self.url).data["words"], self.words)
        with patch("apps.videomanagement.services.captions.transcription.OpenAI") as provider:
            align_scene_narration(self.scene)
        provider.assert_not_called()

    def test_empty_words_hide_scene_captions_and_are_not_retranscribed(self):
        self.assertEqual(self.save(words=[]).status_code, 200)
        self.scene.refresh_from_db()
        self.assertEqual(preview_timeline(self.video).captions, [])
        with patch("apps.videomanagement.services.captions.transcription.OpenAI") as provider:
            align_scene_narration(self.scene)
        provider.assert_not_called()
        self.assertEqual(self.client.get(self.url).data["words"], [])

    def test_estimates_are_editable_and_measured_words_are_preferred_when_available(self):
        data = self.client.get(self.url).data
        self.assertEqual((data["timing"], data["duration"]), ("estimated", 4))
        self.assertEqual(data["audio"], "/voice.wav")
        self.assertEqual([word["text"] for word in data["words"]], ["Hello", "world."])
        self.scene.caption_alignment = {"source": narration_identity(self.scene), "words": self.words}
        self.scene.save(update_fields=["caption_alignment"])
        data = self.client.get(self.url).data
        self.assertEqual((data["timing"], data["words"]), ("measured", self.words))

    def test_invalid_words_are_rejected_without_saving(self):
        invalid = [
            [{"text": "two words", "start": 0, "end": 1}],
            [{"text": "x", "start": -1, "end": 1}],
            [{"text": "x", "start": 1, "end": 1}],
            [{"text": "x", "start": 3, "end": 5}],
            [{"text": "x", "start": 0, "end": 2}, {"text": "y", "start": 1, "end": 3}],
        ]
        for words in invalid:
            with self.subTest(words=words):
                self.assertEqual(self.save(words=words).status_code, 400)
        self.scene.refresh_from_db()
        self.assertEqual(self.scene.caption_alignment, {})

    def test_stale_editor_cannot_overwrite_newer_corrections_or_narration(self):
        revision = self.client.get(self.url).data["revision"]
        self.assertEqual(self.save(revision=revision).status_code, 200)
        self.assertEqual(self.save(revision=revision).status_code, 409)
        revision = self.client.get(self.url).data["revision"]
        self.scene.text = "New narration"
        self.scene.save(update_fields=["text"])
        self.assertEqual(self.save(revision=revision).status_code, 409)

    def test_other_users_cannot_read_or_edit_captions(self):
        revision = self.client.get(self.url).data["revision"]
        self.client.force_authenticate(user.make())
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.save(revision=revision).status_code, 403)

    def test_busy_videos_cannot_be_edited_and_missing_audio_has_clear_error(self):
        revision = self.client.get(self.url).data["revision"]
        self.video.status = "RENDERING"
        self.video.save(update_fields=["status"])
        self.assertEqual(self.save(revision=revision).status_code, 409)
        self.scene.file = None
        self.scene.save(update_fields=["file"])
        self.assertEqual(self.client.get(self.url).status_code, 400)

    def test_saving_unchanged_estimates_preserves_preview_render_and_srt(self):
        self.scene.text = "One two six ten"
        self.scene.save(update_fields=["text"])
        before = preview_timeline(self.video).captions
        srt = export_subtitles(self.video)
        data = self.client.get(self.url).data
        self.assertEqual(self.save(words=data["words"], revision=data["revision"]).status_code, 200)
        self.assertEqual(preview_timeline(self.video).captions, before)
        self.assertEqual(export_subtitles(self.video), srt)
        destination = self.audio.with_suffix(".ass")
        write_captions(destination, preview_timeline(self.video).segments, (1080, 1920))
        rendered = destination.read_text()
        self.assertIn("0:00:00.00,0:00:01.00", rendered)
        self.assertIn("0:00:03.00,0:00:04.00", rendered)
