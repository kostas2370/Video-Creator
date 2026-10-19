import subprocess
import tempfile
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse

from apps.usermanagement.baker_recipes import user
from ...models import AIUsage, CaptionProject
from ...services.captions import process_caption_project, project_cues, write_project_ass
from ...utils.timing import video_metadata
from .base import ApiTestCase


class CaptionProjectTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        override = override_settings(MEDIA_ROOT=self.directory.name)
        override.enable()
        self.addCleanup(override.disable)
        self.source = Path(self.directory.name, "input.mp4")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=blue:s=160x288:r=24:d=1", "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=16000:duration=1", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(self.source)], check=True, capture_output=True, timeout=20)
        queue = patch("apps.videomanagement.tasks.caption_project_task.apply_async")
        self.queue = queue.start()
        self.addCleanup(queue.stop)
        self.url = reverse("captionproject-list")

    def upload(self):
        return self.client.post(self.url, {"source": SimpleUploadedFile("talk.mp4", self.source.read_bytes(), "video/mp4")}, format="multipart")

    def project(self):
        response = self.upload()
        self.assertEqual(response.status_code, 201, response.data)
        return CaptionProject.objects.get(pk=response.data["id"])

    def transcribe(self, project):
        result = SimpleNamespace(words=[SimpleNamespace(word="Hello", start=0.1, end=0.3), SimpleNamespace(word="world.", start=0.45, end=0.8)])
        with patch("apps.videomanagement.services.transcription.OpenAI") as client:
            client.return_value.audio.transcriptions.create.return_value = result
            process_caption_project(str(project.pk), str(project.job_id))
        self.assertEqual(client.return_value.audio.transcriptions.create.call_args.kwargs["timestamp_granularities"], ["word"])
        self.assertEqual(client.return_value.audio.transcriptions.create.call_args.kwargs["model"], "whisper-1")
        project.refresh_from_db()
        self.assertEqual(project.status, "READY", project.error)
        return project

    def test_upload_transcribe_edit_export_and_download_preserve_sound_and_dimensions(self):
        project = self.project()
        self.assertEqual(project.created_by, self.user)
        self.assertEqual(project.status, "QUEUED")
        self.queue.assert_called_once()
        project = self.transcribe(project)
        self.assertTrue(Path(project.preview.path).exists())
        self.assertEqual(project.words[0], {"text": "Hello", "start": 0.1, "end": 0.3})
        self.assertEqual(AIUsage.objects.get(service="stt").seconds, 1)
        words = [{**word, "text": "Hi" if index == 0 else word["text"]} for index, word in enumerate(project.words)]
        response = self.client.patch(reverse("captionproject-detail", args=[project.pk]), {"revision": self.client.get(reverse("captionproject-detail", args=[project.pk])).data["revision"], "words": words, "style": {"preset": "TIKTOK", "color": "#aaffff", "highlight": "#00ff00"}}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        response = self.client.get(reverse("captionproject-subtitles", args=[project.pk]))
        self.assertContains(response, "Hi world.")
        self.assertContains(response, "00:00:00,100 --> 00:00:00,800")
        response = self.client.post(reverse("captionproject-render", args=[project.pk]))
        self.assertEqual(response.status_code, 202, response.data)
        project.refresh_from_db()
        process_caption_project(str(project.pk), str(project.job_id), render=True)
        project.refresh_from_db()
        self.assertEqual(project.status, "COMPLETED", project.error)
        metadata = video_metadata(project.output.path)
        self.assertEqual((metadata["width"], metadata["height"]), (160, 288))
        self.assertTrue(metadata["audio"])
        self.assertAlmostEqual(metadata["duration"], 1, delta=0.1)
        frame = subprocess.run(["ffmpeg", "-v", "error", "-ss", "0.2", "-i", project.output.path, "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"], check=True, capture_output=True, timeout=20).stdout
        green_pixels = sum(g > 130 and r < 100 and b < 100 for r, g, b in zip(frame[::3], frame[1::3], frame[2::3]))
        self.assertGreater(green_pixels, 2)
        response = self.client.get(reverse("captionproject-download", args=[project.pk]))
        self.assertEqual(response.status_code, 200)
        response.close()
        previous_output = project.output.path
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.patch(reverse("captionproject-detail", args=[project.pk]), {"revision": self.client.get(reverse("captionproject-detail", args=[project.pk])).data["revision"], "style": {"position": "top"}}, format="json")
        self.assertEqual(response.status_code, 200)
        project.refresh_from_db()
        self.assertFalse(project.output)
        self.assertFalse(Path(previous_output).exists())
        self.assertEqual(project.style["highlight"], "#00ff00")
        self.assertEqual(self.client.get(reverse("captionproject-download", args=[project.pk])).status_code, 400)

    def test_owner_scoping_applies_to_projects_and_downloads(self):
        project = self.project()
        self.client.force_authenticate(user.make())
        self.assertEqual(self.client.get(self.url).data["count"], 0)
        for name in ("detail", "download", "subtitles"):
            self.assertEqual(self.client.get(reverse(f"captionproject-{name}", args=[project.pk])).status_code, 404)
        self.assertEqual(self.client.patch(reverse("captionproject-detail", args=[project.pk]), {"words": []}, format="json").status_code, 404)
        self.assertEqual(self.client.post(reverse("captionproject-render", args=[project.pk])).status_code, 404)
        self.client.force_authenticate(None)
        self.assertIn(self.client.get(self.url).status_code, (401, 403))

    def test_busy_projects_reject_edits_and_duplicate_jobs(self):
        project = self.project()
        response = self.client.patch(reverse("captionproject-detail", args=[project.pk]), {"words": []}, format="json")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.client.post(reverse("captionproject-transcribe", args=[project.pk])).status_code, 409)
        self.assertEqual(self.queue.call_count, 1)

    def test_invalid_word_times_and_styles_are_rejected(self):
        project = self.project()
        project.status = "READY"
        project.save()
        url = reverse("captionproject-detail", args=[project.pk])
        for words in (
            [{"text": "One", "start": 0.5, "end": 0.1}],
            [{"text": "Two words", "start": 0, "end": 0.5}],
            [{"text": "One", "start": 0, "end": 0.6}, {"text": "Two", "start": 0.5, "end": 0.8}],
            [{"text": "One", "start": 0, "end": 10}],
            [{"text": "One", "start": "NaN", "end": 1}],
        ):
            self.assertEqual(self.client.patch(url, {"words": words}, format="json").status_code, 400)
        for style in ({"size": 100}, {"font": "arbitrary,font"}, {"color": "red"}, {"preset": "INVALID"}):
            self.assertEqual(self.client.patch(url, {"style": style}, format="json").status_code, 400)

    def test_queue_failure_preserves_upload_and_retry_does_not_duplicate_it(self):
        self.queue.side_effect = RuntimeError("Broker unavailable")
        project = self.project()
        self.assertEqual(project.status, "FAILED")
        self.assertTrue(Path(project.source.path).exists())
        self.queue.side_effect = None
        self.assertEqual(self.client.post(reverse("captionproject-transcribe", args=[project.pk])).status_code, 202)
        self.assertEqual(CaptionProject.objects.count(), 1)

    def test_no_speech_and_provider_failure_are_recoverable(self):
        for result in (SimpleNamespace(words=[]), RuntimeError("provider error with private details")):
            project = self.project()
            with patch("apps.videomanagement.services.transcription.OpenAI") as client:
                if isinstance(result, Exception):
                    client.return_value.audio.transcriptions.create.side_effect = result
                else:
                    client.return_value.audio.transcriptions.create.return_value = result
                process_caption_project(str(project.pk), str(project.job_id))
            project.refresh_from_db()
            self.assertEqual(project.status, "FAILED")
            self.assertTrue(project.error)
            self.assertNotIn("private details", project.error)

    def test_stale_or_duplicate_worker_never_calls_the_provider(self):
        project = self.project()
        with patch("apps.videomanagement.services.transcription.OpenAI") as client:
            process_caption_project(str(project.pk), str(uuid4()))
            CaptionProject.objects.filter(pk=project.pk).update(status="TRANSCRIBING")
            process_caption_project(str(project.pk), str(project.job_id))
        client.assert_not_called()

    def test_render_failure_preserves_editable_words(self):
        project = self.project()
        project.status = "READY"
        project.words = [{"text": "Hello", "start": 0.1, "end": 0.8}]
        project.save()
        self.client.post(reverse("captionproject-render", args=[project.pk]))
        project.refresh_from_db()
        with patch("apps.videomanagement.services.captions.run_ffmpeg", side_effect=RuntimeError("encoding failed")):
            process_caption_project(str(project.pk), str(project.job_id), render=True)
        project.refresh_from_db()
        self.assertEqual(project.status, "READY")
        self.assertEqual(project.words[0]["text"], "Hello")
        self.assertIn("export", project.error)
        self.assertNotIn("OpenAI", project.error)

    def test_uploads_without_audio_or_with_invalid_media_are_rejected(self):
        for metadata in (
            {"audio": False, "duration": 1, "width": 100, "height": 100},
            {"audio": True, "duration": 901, "width": 100, "height": 100},
        ):
            with patch("apps.videomanagement.services.caption_uploads.uploaded_video_metadata", return_value=metadata):
                self.assertEqual(self.upload().status_code, 400)
        response = self.client.post(self.url, {"source": SimpleUploadedFile("broken.mp4", b"broken", "video/mp4")}, format="multipart")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(CaptionProject.objects.exists())

    def test_phrase_export_does_not_repeat_words_and_ass_escapes_user_text(self):
        project = self.project()
        project.words = [{"text": "Hi", "start": 0.1, "end": 0.3}, {"text": r"{\pos(0,0)}", "start": 0.4, "end": 0.9}]
        phrases = project_cues(project)
        events = project_cues(project, highlight=True)
        self.assertEqual(len(phrases), 1)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].end, 0.4)
        path = Path(self.directory.name, "captions.ass")
        write_project_ass(project, path)
        self.assertNotIn(r"{\pos", path.read_text())

    def test_stale_editor_cannot_overwrite_newer_words(self):
        project = self.transcribe(self.project())
        url = reverse("captionproject-detail", args=[project.pk])
        stale = self.client.get(url).data
        current_words = [{**word, "text": "New"} for word in project.words]
        response = self.client.patch(url, {"revision": stale["revision"], "words": current_words}, format="json")
        self.assertEqual(response.status_code, 200)
        response = self.client.patch(url, {"revision": stale["revision"], "words": stale["words"], "style": {**stale["style"], "position": "top"}}, format="json")
        self.assertEqual(response.status_code, 409)
        project.refresh_from_db()
        self.assertEqual(project.words, current_words)

    def test_save_requires_revision_and_strict_source_bounds(self):
        project = self.transcribe(self.project())
        url = reverse("captionproject-detail", args=[project.pk])
        self.assertEqual(self.client.patch(url, {"words": project.words}, format="json").status_code, 400)
        revision = self.client.get(url).data["revision"]
        response = self.client.patch(url, {"revision": revision, "words": [{"text": "End", "start": 0, "end": project.duration + 0.005}]}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_reexport_removes_previous_output_after_success(self):
        project = self.transcribe(self.project())
        render_url = reverse("captionproject-render", args=[project.pk])
        for attempt in range(2):
            self.assertEqual(self.client.post(render_url).status_code, 202)
            project.refresh_from_db()
            with self.captureOnCommitCallbacks(execute=True):
                process_caption_project(str(project.pk), str(project.job_id), render=True)
            project.refresh_from_db()
            self.assertEqual(project.status, "COMPLETED", project.error)
            if attempt == 0:
                previous = Path(project.output.path)
        self.assertNotEqual(str(previous), project.output.path)
        self.assertFalse(previous.exists())
        self.assertTrue(Path(project.output.path).exists())
        latest = project.output.path
        self.client.post(render_url)
        project.refresh_from_db()
        with patch("apps.videomanagement.services.captions.run_ffmpeg", side_effect=RuntimeError("encoding failed")):
            process_caption_project(str(project.pk), str(project.job_id), render=True)
        project.refresh_from_db()
        self.assertEqual(project.output.path, latest)
        self.assertTrue(Path(latest).exists())
