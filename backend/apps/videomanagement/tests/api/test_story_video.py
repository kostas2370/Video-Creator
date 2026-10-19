"""Story creation reuses scene jobs, while gameplay loops under the voice."""
import subprocess
import tempfile
import wave
from pathlib import Path
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework.exceptions import NotFound

from ...baker_recipes import voice_model
from ...models import SceneImage, Video, VideoStatus
from ...utils.composer.render import make_video
from ...utils.timing import media_timing
from .base import ApiTestCase


class StoryVideoTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        settings = override_settings(MEDIA_ROOT=self.directory.name)
        settings.enable()
        self.addCleanup(settings.disable)
        self.voice = voice_model.make()
        self.clip = Path(self.directory.name, "gameplay.mp4")
        subprocess.run([
            "ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=red:s=90x160:r=24:d=0.25",
            "-f", "lavfi", "-i", "color=blue:s=90x160:r=24:d=0.25",
            "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]", "-map", "[v]",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", str(self.clip),
        ], capture_output=True, check=True, timeout=30)

    def create(self, **choices):
        return self.client.post(reverse("video-story"), {
            "title": "The unexpected message", "story": "I answered the phone. Everything changed.",
            "voice_id": str(self.voice.pk),
            "gameplay": SimpleUploadedFile("gameplay.mp4", self.clip.read_bytes(), "video/mp4"),
            **choices,
        }, format="multipart")

    def supply_narration(self, scene, *args, **kwargs):
        target = Path(self.directory.name, "narration.wav")
        with wave.open(str(target), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(8000)
            output.writeframes(b"\x10\x00" * 16000)
        scene.file = "narration.wav"
        scene.save()
        return scene

    def test_creates_portrait_draft_and_queues_only_narration(self):
        with patch("apps.videomanagement.tasks.generate_video_task.delay") as generation:
            response = self.create()
        self.assertEqual(response.status_code, 202, response.data)
        generation.assert_not_called()
        video = Video.objects.get(pk=response.data["id"])
        self.assertEqual(video.created_by, self.user)
        self.assertEqual(video.status, VideoStatus.GENERATION)
        self.assertEqual(video.voice_model, self.voice)
        self.assertEqual(video.settings["video_format"], "PORTRAIT")
        self.assertEqual(video.settings["platform"], "TIKTOK")
        self.assertTrue(video.settings["subtitles"])
        self.assertTrue(video.settings["loop_visual"])
        self.assertFalse(video.scenes.get().scene_images.get().with_audio)
        with patch("apps.videomanagement.services.scenes.narration.narrate_scene", side_effect=self.supply_narration):
            self.run_scene_job()
        video.refresh_from_db()
        self.assertEqual(video.status, VideoStatus.READY)
        preview = self.client.get(reverse("video-preview", args=[video.pk]))
        self.assertEqual(preview.status_code, 200, preview.data)
        self.assertEqual(preview.data["size"], [1080, 1920])
        self.assertTrue(preview.data["segments"][0]["loop_visual"])
        self.assertFalse(preview.data["segments"][0]["clip_audio"])
        self.assertAlmostEqual(preview.data["duration"], 2, delta=0.05)
        self.assertAlmostEqual(preview.data["captions"][-1]["end"], 2, delta=0.05)
        self.assertEqual(len(preview.data["audio_tracks"]), 1)
        export = self.client.get(reverse("video-subtitles", args=[video.pk]))
        self.assertIn("Everything changed.", export.content.decode())

    def test_render_repeats_motion_beyond_original_clip_and_stops_at_voice_end(self):
        response = self.create(subtitles=False)
        self.assertEqual(response.status_code, 202, response.data)
        with patch("apps.videomanagement.services.scenes.narration.narrate_scene", side_effect=self.supply_narration):
            self.run_scene_job()
        video = Video.objects.get(pk=response.data["id"])
        with patch("apps.videomanagement.utils.composer.render.output_size", return_value=(90, 160)):
            make_video(video)
        self.assertAlmostEqual(media_timing(video.output.path)["duration"], 2, delta=0.1)
        # The second loop must contain both colors, rather than holding the final blue frame.
        for timestamp, channel in ((0.62, 0), (0.87, 2), (1.62, 0), (1.87, 2)):
            frame = subprocess.run([
                "ffmpeg", "-v", "error", "-ss", str(timestamp), "-i", video.output.path,
                "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1",
            ], capture_output=True, check=True, timeout=30).stdout
            self.assertGreater(frame[channel], 220)

    def test_story_text_edits_and_missing_narration_retry_use_voice_jobs(self):
        response = self.create()
        video = Video.objects.get(pk=response.data["id"])
        with patch("apps.videomanagement.services.scenes.narration.narrate_scene", side_effect=RuntimeError("Provider down")):
            with self.assertRaises(RuntimeError):
                self.run_scene_job()
        video.refresh_from_db()
        self.assertEqual(video.status, VideoStatus.READY)
        scene = video.scenes.get()
        response = self.client.patch(reverse("scene-detail", args=[scene.pk]), {"text": "A different story."}, format="json")
        self.assertEqual(response.status_code, 202, response.data)
        with patch("apps.videomanagement.services.scenes.narration.narrate_scene", side_effect=self.supply_narration):
            result = self.run_scene_job()
        self.assertEqual(result["narration_status"], "available")
        scene.refresh_from_db()
        self.assertEqual(scene.text, "A different story.")

    def test_broker_failure_keeps_editable_project_with_retry_notice(self):
        with patch("apps.videomanagement.tasks.update_scene_task.apply_async", side_effect=RuntimeError("Broker down")):
            response = self.create()
        self.assertEqual(response.status_code, 201, response.data)
        self.assertIn("Retry narration", response.data["warning"])
        video = Video.objects.get(pk=response.data["id"])
        self.assertEqual(video.status, VideoStatus.READY)
        self.assertTrue(Path(video.scenes.get().scene_images.get().file.path).exists())

    def test_rejects_invalid_story_clip_and_voice_before_creating_project(self):
        for choices in (
            {"story": " "}, {"story": "a" * 2001}, {"voice_id": ""},
            {"voice_id": "00000000-0000-0000-0000-000000000000"},
            {"gameplay": SimpleUploadedFile("photo.png", b"not gameplay")},
            {"gameplay": SimpleUploadedFile("broken.mp4", b"not video")},
        ):
            with self.subTest(choices=list(choices)):
                response = self.create(**choices)
                self.assertIn(response.status_code, (400, 404), response.data)
        self.assertFalse(Video.objects.exists())
        self.assertFalse(SceneImage.objects.exists())
        self.scene_queue.assert_not_called()

    def test_unavailable_voice_and_unauthenticated_creation_are_rejected(self):
        with patch("apps.videomanagement.serializers.requests.available_voice", side_effect=NotFound("Voice is unavailable.")):
            self.assertEqual(self.create().status_code, 404)
        self.client.force_authenticate(None)
        self.assertIn(self.create().status_code, (401, 403))
        self.assertFalse(Video.objects.exists())
