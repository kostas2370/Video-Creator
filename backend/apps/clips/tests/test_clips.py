import json
import subprocess
import tempfile
from datetime import timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

from django.core.files import File
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.clips.highlights import suggest_clips
from apps.clips.models import Clip, ClipProject
from apps.clips.processing import process_project, transcribe_source
from apps.clips.rendering import export_clip
from apps.clips.services import clip_words, queue_exports, queue_project
from apps.usermanagement.baker_recipes import user
from apps.videomanagement.utils.timing import video_metadata


class ClipsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media = tempfile.TemporaryDirectory()
        cls.override = override_settings(MEDIA_ROOT=cls.media.name)
        cls.override.enable()
        cls.source = Path(cls.media.name, "test.mp4")
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "color=blue:s=160x90:r=12:d=20",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:sample_rate=16000:duration=20",
                "-c:v",
                "libx264",
                "-c:a",
                "aac",
                "-pix_fmt",
                "yuv420p",
                str(cls.source),
            ],
            check=True,
            capture_output=True,
            timeout=30,
        )

    @classmethod
    def tearDownClass(cls):
        cls.override.disable()
        cls.media.cleanup()
        super().tearDownClass()

    def setUp(self):
        self.user = user.make()
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.words = [
            {"text": f"Word{index}", "start": float(index), "end": index + 0.8}
            for index in range(20)
        ]
        self.project_queue = patch(
            "apps.clips.tasks.process_project_task.apply_async"
        ).start()
        self.export_queue = patch(
            "apps.clips.tasks.export_clip_task.apply_async"
        ).start()
        patch(
            "apps.videomanagement.throttling.BaseThrottle.allow_request",
            return_value=True,
        ).start()
        self.addCleanup(patch.stopall)

    def project(self, **kwargs):
        with self.source.open("rb") as file:
            return ClipProject.objects.create(
                created_by=self.user,
                source=File(file, "input.mp4"),
                title="Interview",
                duration=20,
                width=160,
                height=90,
                min_duration=10,
                max_duration=15,
                words=self.words,
                status="READY",
                **kwargs,
            )

    def detail(self, project):
        return reverse("clipproject-detail", args=[project.pk])

    def add(self, project, **changes):
        return self.client.post(
            reverse("clipproject-clips", args=[project.pk]),
            {"start": 1, "end": 13, **changes},
            format="json",
        )

    def clip_url(self, clip):
        return reverse(
            "clipproject-clip", kwargs={"pk": clip.project_id, "clip_id": clip.pk}
        )

    def edit(self, clip, **changes):
        revision = self.client.get(self.detail(clip.project)).data["clips"][0][
            "revision"
        ]
        return self.client.patch(
            self.clip_url(clip), {"revision": revision, **changes}, format="json"
        )

    def test_upload_queues_processing_and_retains_source_on_dispatch_failure(self):
        self.project_queue.side_effect = RuntimeError("broker unavailable")
        response = self.client.post(
            reverse("clipproject-list"),
            {
                "source": SimpleUploadedFile("talk.mp4", self.source.read_bytes()),
                "min_duration": 10,
                "max_duration": 15,
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 201, response.data)
        project = ClipProject.objects.get()
        self.assertEqual(project.status, "FAILED")
        self.assertTrue(Path(project.source.path).exists())
        self.project_queue.side_effect = None
        response = self.client.post(reverse("clipproject-retry", args=[project.pk]))
        self.assertEqual(response.status_code, 202)
        self.assertEqual(ClipProject.objects.count(), 1)

    def test_upload_checks_source_duration_audio_and_options(self):
        with patch(
            "apps.clips.uploads.uploaded_video_metadata",
            return_value={
                "duration": 8000,
                "audio": True,
                "width": 1920,
                "height": 1080,
            },
        ):
            response = self.client.post(
                reverse("clipproject-list"),
                {"source": SimpleUploadedFile("talk.mp4", b"data")},
                format="multipart",
            )
        self.assertEqual(response.status_code, 400)
        with patch(
            "apps.clips.uploads.uploaded_video_metadata",
            return_value={
                "duration": 60,
                "audio": False,
                "width": 1920,
                "height": 1080,
            },
        ):
            response = self.client.post(
                reverse("clipproject-list"),
                {"source": SimpleUploadedFile("talk.mp4", b"data")},
                format="multipart",
            )
        self.assertEqual(response.status_code, 400)
        self.project_queue.assert_not_called()

    def test_other_users_cannot_read_edit_export_or_download_a_project(self):
        project = self.project()
        clip = Clip.objects.create(project=project, title="Private", start=0, end=12)
        self.client.force_authenticate(user.make())
        self.assertEqual(self.client.get(self.detail(project)).status_code, 404)
        self.assertEqual(
            self.client.patch(self.clip_url(clip), {}, format="json").status_code, 404
        )
        self.assertEqual(
            self.client.post(
                reverse("clipproject-export", args=[project.pk]),
                {"clip_ids": [str(clip.pk)]},
                format="json",
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(
                reverse(
                    "clipproject-download",
                    kwargs={"pk": project.pk, "clip_id": clip.pk},
                )
            ).status_code,
            404,
        )
        self.assertEqual(self.client.get(reverse("clipproject-list")).data["count"], 0)

    def test_manual_clips_rebase_captions_and_trim_resets_words(self):
        project = self.project()
        response = self.add(project)
        self.assertEqual(response.status_code, 201, response.data)
        clip = project.clips.get()
        self.assertEqual(clip.words[0]["start"], 0)
        self.assertEqual(clip.words[-1]["text"], "Word12")
        response = self.edit(clip, start=2, end=14)
        self.assertEqual(response.status_code, 200, response.data)
        clip.refresh_from_db()
        self.assertEqual(clip.words[0]["text"], "Word2")
        self.assertEqual(clip.words[0]["start"], 0)

    def test_stale_edits_invalid_times_and_cross_project_clip_ids_are_rejected(self):
        project = self.project()
        clip = Clip.objects.get(pk=self.add(project).data["id"])
        response = self.client.patch(
            self.clip_url(clip), {"title": "Missing revision"}, format="json"
        )
        self.assertEqual(response.status_code, 409)
        revision = self.client.get(self.detail(project)).data["clips"][0]["revision"]
        self.assertEqual(self.edit(clip, title="New title").status_code, 200)
        self.assertEqual(
            self.client.patch(
                self.clip_url(clip),
                {"revision": revision, "title": "Stale"},
                format="json",
            ).status_code,
            409,
        )
        for changes in (
            {"end": 21},
            {"start": 14, "end": 13},
            {"start": -1},
            {"crop_position": 101},
        ):
            self.assertEqual(self.edit(clip, **changes).status_code, 400)
        other = self.project()
        self.assertEqual(
            self.client.post(
                reverse("clipproject-export", args=[other.pk]),
                {"clip_ids": [str(clip.pk)]},
                format="json",
            ).status_code,
            400,
        )

    def test_busy_clips_cannot_be_changed_and_duplicate_exports_do_not_dispatch(self):
        project = self.project()
        clip = Clip.objects.get(pk=self.add(project).data["id"])
        queue_exports(project, [clip.pk])
        self.assertEqual(self.edit(clip, title="No").status_code, 409)
        self.assertEqual(self.client.delete(self.clip_url(clip)).status_code, 409)
        self.assertEqual(
            self.client.post(
                reverse("clipproject-export", args=[project.pk]),
                {"clip_ids": [str(clip.pk)]},
                format="json",
            ).status_code,
            409,
        )
        self.export_queue.assert_called_once()

    def test_batch_exports_fail_independently_and_stale_jobs_can_be_retried(self):
        project = self.project()
        a = Clip.objects.get(pk=self.add(project).data["id"])
        b = Clip.objects.get(pk=self.add(project).data["id"])
        self.export_queue.side_effect = [RuntimeError("broker"), None]
        results = queue_exports(project, [a.pk, b.pk])
        self.assertEqual(sorted(item.status for item in results), ["FAILED", "QUEUED"])
        queued = next(item for item in results if item.status == "QUEUED")
        Clip.objects.filter(pk=queued.pk).update(
            updated_at=timezone.now() - timedelta(hours=4)
        )
        self.export_queue.side_effect = None
        self.assertEqual(queue_exports(project, [queued.pk])[0].status, "QUEUED")

    def test_ai_suggestions_reject_invalid_ranges_and_remove_overlapping_excerpts(self):
        project = self.project()
        raw = {
            "clips": [
                {
                    "first_word": 0,
                    "last_word": 12,
                    "title": "A",
                    "reason": "Complete explanation",
                },
                {
                    "first_word": 1,
                    "last_word": 13,
                    "title": "Duplicate",
                    "reason": "Same passage",
                },
                {
                    "first_word": 0,
                    "last_word": 2000,
                    "title": "Invalid",
                    "reason": "Out of range",
                },
                {
                    "first_word": 2,
                    "last_word": 3,
                    "title": "Too short",
                    "reason": "Short",
                },
            ]
        }
        with patch(
            "apps.clips.highlights.get_update_sentence", return_value=json.dumps(raw)
        ):
            candidates = suggest_clips(project)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["start"], 0)
        self.assertEqual(candidates[0]["end"], 12.8)

    def test_analysis_failure_reuses_saved_preview_and_transcript_on_retry(self):
        project = self.project()
        project.preview = project.source.name
        project.status = "FAILED"
        project.save()
        queue_project(project)
        project.refresh_from_db()
        with (
            patch(
                "apps.clips.processing.suggest_clips",
                side_effect=ValueError("provider secret"),
            ),
            patch("apps.clips.processing.transcribe_audio") as transcribe,
        ):
            process_project(project.pk, project.job_id)
        transcribe.assert_not_called()
        project.refresh_from_db()
        self.assertEqual(project.status, "FAILED")
        self.assertNotIn("provider secret", project.error)
        queue_project(project)
        project.refresh_from_db()
        with (
            patch(
                "apps.clips.processing.suggest_clips",
                return_value=[
                    {
                        "title": "An answer",
                        "reason": "Complete thought",
                        "start": 1,
                        "end": 13,
                    }
                ],
            ),
            patch("apps.clips.processing.transcribe_audio") as transcribe,
        ):
            process_project(project.pk, project.job_id)
        project.refresh_from_db()
        self.assertEqual(project.status, "READY")
        self.assertEqual(project.clips.count(), 1)
        transcribe.assert_not_called()

    def test_wrong_tokens_and_duplicate_deliveries_do_not_call_providers(self):
        project = self.project()
        with (
            patch("apps.clips.processing.suggest_clips") as suggest,
            patch("apps.clips.processing.make_preview") as preview,
        ):
            process_project(project.pk, uuid4())
            process_project(project.pk, project.job_id)
        suggest.assert_not_called()
        preview.assert_not_called()

    def test_transcription_chunks_checkpoint_before_later_failure_and_resume(self):
        project = self.project()
        project.duration, project.status, project.job_id, project.words = (
            1201,
            "TRANSCRIBING",
            uuid4(),
            [],
        )
        project.save()
        rows = ClipProject.objects.filter(pk=project.pk, job_id=project.job_id)
        with (
            tempfile.TemporaryDirectory() as directory,
            patch("apps.clips.processing.run_ffmpeg"),
            patch(
                "apps.clips.processing.transcribe_audio",
                side_effect=[
                    [{"text": "First", "start": 0, "end": 1}],
                    RuntimeError("provider"),
                ],
            ),
        ):
            with self.assertRaises(RuntimeError):
                transcribe_source(project, rows, directory)
        project.refresh_from_db()
        self.assertEqual(len(project.transcript_parts), 1)
        with (
            tempfile.TemporaryDirectory() as directory,
            patch("apps.clips.processing.run_ffmpeg"),
            patch(
                "apps.clips.processing.transcribe_audio",
                return_value=[{"text": "Next", "start": 2, "end": 3}],
            ) as transcribe,
        ):
            words = transcribe_source(project, rows, directory)
        self.assertEqual(transcribe.call_count, 2)
        self.assertEqual([word["start"] for word in words], [0, 600, 1200])

    def test_real_upload_processing_creates_playable_preview_without_paid_requests(
        self,
    ):
        project = self.project()
        project.words, project.status, project.job_id = [], "QUEUED", uuid4()
        project.save()
        with (
            patch("apps.clips.processing.transcribe_audio", return_value=self.words),
            patch("apps.clips.processing.suggest_clips", return_value=[]),
        ):
            process_project(project.pk, project.job_id)
        project.refresh_from_db()
        self.assertEqual(project.status, "READY", project.error)
        self.assertTrue(Path(project.preview.path).exists())
        self.assertEqual(project.words, self.words)

    def test_real_portrait_exports_have_correct_duration_audio_and_captions(self):
        project = self.project()
        for layout in ("CROP", "FIT"):
            clip = Clip.objects.create(
                project=project,
                title=layout,
                start=1,
                end=3,
                layout=layout,
                words=clip_words(self.words, 1, 3),
                style={"color": "#00ff00", "highlight": "#00ff00"},
            )
            queue_exports(project, [clip.pk])
            clip.refresh_from_db()
            export_clip(clip.pk, clip.job_id)
            clip.refresh_from_db()
            self.assertEqual(clip.status, "COMPLETED", clip.error)
            metadata = video_metadata(clip.output.path)
            self.assertEqual((metadata["width"], metadata["height"]), (720, 1280))
            self.assertAlmostEqual(metadata["duration"], 2, delta=0.15)
            self.assertTrue(metadata["audio"])
            frame = subprocess.run(
                [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-ss",
                    "0.2",
                    "-i",
                    clip.output.path,
                    "-frames:v",
                    "1",
                    "-f",
                    "rawvideo",
                    "-pix_fmt",
                    "rgb24",
                    "pipe:1",
                ],
                check=True,
                capture_output=True,
                timeout=20,
            ).stdout
            green = sum(
                g > 130 and r < 100 and b < 100
                for r, g, b in zip(frame[::3], frame[1::3], frame[2::3])
            )
            self.assertGreater(green, 5)
            response = self.client.get(
                reverse(
                    "clipproject-download",
                    kwargs={"pk": project.pk, "clip_id": clip.pk},
                )
            )
            self.assertEqual(response.status_code, 200)
            response.close()

    def test_failed_export_preserves_previous_output_and_can_retry(self):
        project = self.project()
        clip = Clip.objects.create(
            project=project, title="A", start=1, end=3, output="media/previous.mp4"
        )
        queue_exports(project, [clip.pk])
        clip.refresh_from_db()
        with patch(
            "apps.clips.media.subprocess.run",
            side_effect=RuntimeError("private path"),
        ):
            export_clip(clip.pk, clip.job_id)
        clip.refresh_from_db()
        self.assertEqual(clip.status, "FAILED")
        self.assertEqual(clip.output.name, "media/previous.mp4")
        self.assertNotIn("private path", clip.error)
        self.assertEqual(queue_exports(project, [clip.pk])[0].status, "QUEUED")

    def test_anonymous_requests_cannot_use_clipping(self):
        self.client.force_authenticate(None)
        self.assertIn(
            self.client.get(reverse("clipproject-list")).status_code, [401, 403]
        )

    def test_global_ranking_uses_distinct_valid_candidates(self):
        project = self.project()
        project.clip_count = 1
        project.words = [
            {"text": f"Word{index}", "start": float(index), "end": index + 0.8}
            for index in range(1400)
        ]
        first = {
            "clips": [
                {"first_word": 0, "last_word": 12, "title": "First", "reason": "A"}
            ]
        }
        second = {
            "clips": [
                {
                    "first_word": 1100,
                    "last_word": 1112,
                    "title": "Second",
                    "reason": "B",
                }
            ]
        }
        with patch(
            "apps.clips.highlights.get_update_sentence",
            side_effect=[json.dumps(first), json.dumps(second), '{"indices": [1]}'],
        ):
            result = suggest_clips(project)
        self.assertEqual([item["title"] for item in result], ["Second"])
        with patch(
            "apps.clips.highlights.get_update_sentence",
            side_effect=[json.dumps(first), json.dumps(second), '{"indices": [200]}'],
        ):
            with self.assertRaises(ValueError):
                suggest_clips(project)

    def test_analysis_retry_preserves_manual_clips_and_adds_nonoverlapping_suggestions(
        self,
    ):
        project = self.project()
        project.duration = 100
        project.status, project.job_id = "QUEUED", uuid4()
        project.preview = project.source.name
        project.save()
        manual = Clip.objects.create(project=project, title="My edit", start=0, end=12)
        with patch(
            "apps.clips.processing.suggest_clips",
            return_value=[
                {"title": "Duplicate", "reason": "Overlap", "start": 1, "end": 13},
                {"title": "New", "reason": "New thought", "start": 40, "end": 52},
            ],
        ):
            process_project(project.pk, project.job_id)
        manual.refresh_from_db()
        self.assertEqual(manual.title, "My edit")
        self.assertEqual(
            set(project.clips.values_list("title", flat=True)), {"My edit", "New"}
        )

    def test_saving_one_clip_invalidates_only_its_own_export(self):
        project = self.project()
        a = Clip.objects.get(pk=self.add(project).data["id"])
        b = Clip.objects.get(pk=self.add(project).data["id"])
        Clip.objects.filter(pk__in=[a.pk, b.pk]).update(
            status="COMPLETED", output="media/saved.mp4"
        )
        self.assertEqual(self.edit(a, crop_position=25).status_code, 200)
        a.refresh_from_db()
        b.refresh_from_db()
        self.assertEqual(a.output.name, "")
        self.assertEqual(a.status, "READY")
        self.assertEqual(b.output.name, "media/saved.mp4")
        self.assertEqual(b.status, "COMPLETED")

    def test_export_duplicate_delivery_does_not_render_twice(self):
        project = self.project()
        clip = Clip.objects.create(
            project=project,
            title="Done",
            start=0,
            end=2,
            status="COMPLETED",
            job_id=uuid4(),
        )
        with patch("apps.clips.media.subprocess.run") as run:
            export_clip(clip.pk, clip.job_id)
            export_clip(clip.pk, uuid4())
        run.assert_not_called()

    def hashtags_url(self, clip):
        return reverse(
            "clipproject-hashtags", kwargs={"pk": clip.project_id, "clip_id": clip.pk}
        )

    def test_hashtag_generation_is_a_reviewable_draft_and_uses_clip_words(self):
        project = self.project()
        clip = Clip.objects.get(pk=self.add(project).data["id"])
        with patch(
            "apps.clips.hashtags.get_update_sentence",
            return_value='{"hashtags": ["#Interview", "interview", "Discussion"]}',
        ) as generate:
            response = self.client.post(self.hashtags_url(clip), {}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["hashtags"], ["Interview", "Discussion"])
        self.assertIn("Word1", generate.call_args.args[0])
        self.assertNotIn("Word19", generate.call_args.args[0])
        clip.refresh_from_db()
        self.assertEqual(clip.hashtags, [])

    def test_hashtag_save_normalizes_values_and_keeps_export_and_editor_revision(self):
        project = self.project()
        clip = Clip.objects.get(pk=self.add(project).data["id"])
        Clip.objects.filter(pk=clip.pk).update(
            status="COMPLETED", output="media/export.mp4"
        )
        clip.refresh_from_db()
        revision = clip.updated_at
        response = self.client.patch(
            self.hashtags_url(clip),
            {"hashtags": ["#Topic", "topic", "Short_Clips"], "previous_hashtags": []},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        clip.refresh_from_db()
        self.assertEqual(clip.hashtags, ["Topic", "Short_Clips"])
        self.assertEqual(clip.updated_at, revision)
        self.assertEqual(clip.status, "COMPLETED")
        self.assertEqual(clip.output.name, "media/export.mp4")

    def test_hashtags_reject_invalid_values_and_concurrent_overwrites(self):
        project = self.project()
        clip = Clip.objects.get(pk=self.add(project).data["id"])
        for values in (["wrong!"], [123], ["a"] * 21):
            response = self.client.patch(
                self.hashtags_url(clip),
                {"hashtags": values, "previous_hashtags": []},
                format="json",
            )
            self.assertEqual(response.status_code, 400, response.data)
        clip.hashtags = ["Saved"]
        clip.save(update_fields=["hashtags"])
        response = self.client.patch(
            self.hashtags_url(clip),
            {"hashtags": ["Stale"], "previous_hashtags": []},
            format="json",
        )
        self.assertEqual(response.status_code, 409)
        with patch(
            "apps.clips.hashtags.get_update_sentence",
            return_value='{"hashtags": ["invalid!"]}',
        ):
            response = self.client.post(self.hashtags_url(clip), {}, format="json")
        self.assertEqual(response.status_code, 500)
        clip.refresh_from_db()
        self.assertEqual(clip.hashtags, ["Saved"])

    def test_hashtags_are_scoped_to_the_project_owner(self):
        project = self.project()
        clip = Clip.objects.get(pk=self.add(project).data["id"])
        self.client.force_authenticate(user.make())
        with patch("apps.clips.hashtags.get_update_sentence") as generate:
            self.assertEqual(
                self.client.post(
                    self.hashtags_url(clip), {}, format="json"
                ).status_code,
                404,
            )
            self.assertEqual(
                self.client.patch(
                    self.hashtags_url(clip),
                    {"hashtags": [], "previous_hashtags": []},
                    format="json",
                ).status_code,
                404,
            )
        generate.assert_not_called()

    def test_extraction_brief_is_optional_nullable_and_used_in_highlight_selection(
        self,
    ):
        from apps.clips.serializers import ProjectUploadSerializer

        for value in (None, "", "   ", "  Focus on business advice  "):
            serializer = ProjectUploadSerializer(
                data={
                    "source": SimpleUploadedFile("talk.mp4", self.source.read_bytes()),
                    "min_duration": 10,
                    "max_duration": 15,
                    "extraction_prompt": value,
                }
            )
            self.assertTrue(serializer.is_valid(), serializer.errors)
            self.assertEqual(
                serializer.validated_data["extraction_prompt"],
                value.strip() or None if value is not None else None,
            )
        project = self.project(extraction_prompt="Focus on business advice")
        with patch(
            "apps.clips.highlights.get_update_sentence", return_value='{"clips": []}'
        ) as generate:
            suggest_clips(project)
        self.assertIn(
            '"extraction_brief": "Focus on business advice"', generate.call_args.args[0]
        )
        self.assertEqual(
            self.client.get(self.detail(project)).data["extraction_prompt"],
            "Focus on business advice",
        )

    def test_upload_persists_extraction_brief_and_missing_brief_defaults_to_null(self):
        for supplied in (
            {},
            {"extraction_prompt": "Interesting technical explanations"},
        ):
            response = self.client.post(
                reverse("clipproject-list"),
                {
                    "source": SimpleUploadedFile("talk.mp4", self.source.read_bytes()),
                    "min_duration": 10,
                    "max_duration": 15,
                    **supplied,
                },
                format="multipart",
            )
            self.assertEqual(response.status_code, 201, response.data)
            self.assertEqual(
                response.data["extraction_prompt"], supplied.get("extraction_prompt")
            )

    def test_non_english_hashtags_are_retried_then_rejected_without_saving(self):
        project = self.project()
        clip = Clip.objects.get(pk=self.add(project).data["id"])
        with patch(
            "apps.clips.hashtags.get_update_sentence",
            side_effect=[
                '{"hashtags": ["Συζήτηση"]}',
                '{"hashtags": ["Discussion", "HarryPotter"]}',
            ],
        ) as generate:
            response = self.client.post(self.hashtags_url(clip), {}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["hashtags"], ["Discussion", "HarryPotter"])
        self.assertEqual(generate.call_count, 2)
        self.assertIn("Translate topic words", generate.call_args.args[0])
        with patch(
            "apps.clips.hashtags.get_update_sentence",
            return_value='{"hashtags": ["Συζήτηση"]}',
        ) as generate:
            response = self.client.post(self.hashtags_url(clip), {}, format="json")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(generate.call_count, 2)
        response = self.client.patch(
            self.hashtags_url(clip),
            {"hashtags": ["Συζήτηση"], "previous_hashtags": []},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        clip.refresh_from_db()
        self.assertEqual(clip.hashtags, [])

    def test_hashtag_prompt_requires_supported_person_and_character_name_tags_in_english(
        self,
    ):
        project = self.project()
        clip = Clip.objects.get(pk=self.add(project).data["id"])
        clip.title = "Harry Potter meets Hermione Granger"
        clip.save(update_fields=["title"])
        with patch(
            "apps.clips.hashtags.get_update_sentence",
            return_value='{"hashtags": ["HarryPotter", "HermioneGranger", "WizardingWorld"]}',
        ) as generate:
            response = self.client.post(self.hashtags_url(clip), {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("HarryPotter", response.data["hashtags"])
        prompt = generate.call_args.args[0]
        self.assertIn("a name hashtag for each person or fictional character", prompt)
        self.assertIn("Do not invent identities", prompt)
        self.assertIn("ALL hashtags in English", prompt)
        self.assertIn(clip.title, prompt)

    def test_title_only_and_unchanged_edits_preserve_a_completed_export(self):
        project = self.project()
        clip = Clip.objects.get(pk=self.add(project).data["id"])
        Clip.objects.filter(pk=clip.pk).update(
            status="COMPLETED", output="media/saved.mp4"
        )
        self.assertEqual(self.edit(clip, title="A better title").status_code, 200)
        self.assertEqual(self.edit(clip, crop_position=50).status_code, 200)
        clip.refresh_from_db()
        self.assertEqual(clip.output.name, "media/saved.mp4")
        self.assertEqual(clip.status, "COMPLETED")

    def test_caption_bounds_are_checked_before_invalidating_a_saved_export(self):
        project = self.project()
        clip = Clip.objects.get(pk=self.add(project).data["id"])
        Clip.objects.filter(pk=clip.pk).update(
            status="COMPLETED", output="media/saved.mp4"
        )
        for words in (
            [{"text": "Outside", "start": 0, "end": 15}],
            [
                {"text": "First", "start": 0, "end": 2},
                {"text": "Overlap", "start": 1, "end": 3},
            ],
        ):
            self.assertEqual(self.edit(clip, words=words).status_code, 400)
        clip.refresh_from_db()
        self.assertEqual(clip.output.name, "media/saved.mp4")
        self.assertEqual(clip.status, "COMPLETED")

    def test_project_deletion_waits_for_fresh_jobs_and_allows_stalled_job_cleanup(self):
        project = self.project()
        clip = Clip.objects.get(pk=self.add(project).data["id"])
        queue_exports(project, [clip.pk])
        self.assertEqual(self.client.delete(self.detail(project)).status_code, 409)
        Clip.objects.filter(pk=clip.pk).update(
            updated_at=timezone.now() - timedelta(hours=4)
        )
        self.assertEqual(self.client.delete(self.detail(project)).status_code, 204)
        self.assertFalse(ClipProject.objects.filter(pk=project.pk).exists())

    def test_deleted_objects_return_not_found_when_service_lock_is_acquired(self):
        from django.http import Http404

        from apps.clips.hashtags import save_hashtags
        from apps.clips.services import delete_clip, delete_project, save_clip

        project = self.project()
        clip = Clip.objects.get(pk=self.add(project).data["id"])
        Clip.objects.filter(pk=clip.pk).delete()
        with self.assertRaises(Http404):
            delete_clip(project, clip.pk)
        with self.assertRaises(Http404):
            save_hashtags(clip, hashtags=[], previous_hashtags=[])
        ClipProject.objects.filter(pk=project.pk).delete()
        with self.assertRaises(Http404):
            delete_project(project)
        with self.assertRaises(Http404):
            save_clip(project, {"start": 0, "end": 10})

    def test_clip_media_is_private_and_supports_authenticated_byte_ranges(self):
        import asyncio

        project = self.project()
        self.assertIn("private-clips", project.source.path)
        self.assertFalse(Path(self.media.name, project.source.name).exists())
        url = reverse("clipproject-source", args=[project.pk])
        response = self.client.get(url, HTTP_RANGE="bytes=2-9")
        self.assertEqual(response.status_code, 206)
        self.assertEqual(response["Content-Length"], "8")
        self.assertIn("private", response["Cache-Control"])

        async def content():
            return b"".join([chunk async for chunk in response.streaming_content])

        self.assertEqual(
            asyncio.run(content()), Path(project.source.path).read_bytes()[2:10]
        )
        self.assertEqual(
            self.client.get(url, HTTP_RANGE="bytes=999999999-").status_code, 416
        )
        self.assertEqual(
            self.client.get(url, HTTP_RANGE="bytes=0-1,3-4").status_code, 416
        )
        self.assertEqual(
            self.client.head(url)["Content-Length"], str(project.source.size)
        )
        data = self.client.get(self.detail(project)).data
        self.assertIn(f"/api/clips/{project.pk}/source/", data["source"])
        self.assertNotIn("media/clips", data["source"])
        self.assertEqual(self.client.get("/" + project.source.name).status_code, 404)
        self.client.force_authenticate(user.make())
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(url).status_code, 401)

    def test_progress_omits_transcripts_and_reaps_exports_after_thirty_minutes(self):
        project = self.project()
        clip = Clip.objects.get(pk=self.add(project).data["id"])
        queue_exports(project, [clip.pk])
        token = Clip.objects.get(pk=clip.pk).job_id
        Clip.objects.filter(pk=clip.pk).update(
            updated_at=timezone.now() - timedelta(minutes=31)
        )
        from apps.clips.services import reap_stalled_exports

        self.assertEqual(reap_stalled_exports(project.pk), 1)
        response = self.client.get(reverse("clipproject-progress", args=[project.pk]))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["has_transcript"])
        self.assertNotIn("words", response.data)
        self.assertNotIn("words", response.data["clips"][0])
        self.assertNotIn("style", response.data["clips"][0])
        self.assertEqual(response.data["clips"][0]["status"], "FAILED")
        self.assertTrue(response.data["clips"][0]["can_retry"])
        with patch("apps.clips.media.subprocess.run") as run:
            export_clip(clip.pk, token)
        run.assert_not_called()
        self.assertEqual(queue_exports(project, [clip.pk])[0].status, "QUEUED")

    def test_export_retry_threshold_matches_progress_and_preserves_fresh_exports(self):
        from apps.clips.services import reap_stalled_exports

        project = self.project()
        clip = Clip.objects.get(pk=self.add(project).data["id"])
        queue_exports(project, [clip.pk])
        Clip.objects.filter(pk=clip.pk).update(
            updated_at=timezone.now() - timedelta(minutes=29)
        )
        self.assertEqual(reap_stalled_exports(project.pk), 0)
        self.assertEqual(
            self.client.post(
                reverse("clipproject-export", args=[project.pk]),
                {"clip_ids": [str(clip.pk)]},
                format="json",
            ).status_code,
            409,
        )
        Clip.objects.filter(pk=clip.pk).update(
            updated_at=timezone.now() - timedelta(minutes=31)
        )
        self.assertEqual(queue_exports(project, [clip.pk])[0].status, "QUEUED")

    def test_job_updates_publish_after_commit_without_exposing_transcripts(self):
        project = self.project()
        with patch("apps.videomanagement.events.send_event") as send:
            with self.captureOnCommitCallbacks(execute=True):
                self.add(project)
            self.assertEqual(send.call_args.args[0], f"clips.{project.pk}")
            self.assertEqual(send.call_args.args[2]["kind"], "clips")
            self.assertNotIn("words", send.call_args.args[2])

    def test_existing_public_files_are_moved_to_private_storage(self):
        import importlib

        from django.apps import apps

        migration = importlib.import_module(
            "apps.clips.migrations.0004_alter_clip_output_alter_clipproject_preview_and_more"
        )
        project = self.project()
        name = f"media/clips/{project.pk}/legacy.mp4"
        public = Path(self.media.name, name)
        public.parent.mkdir(parents=True, exist_ok=True)
        public.write_bytes(b"legacy-content")
        project.source.name = name
        project.save(update_fields=["source"])
        migration.move_to_private_storage(apps, None)
        self.assertFalse(public.exists())
        self.assertEqual(Path(project.source.path).read_bytes(), b"legacy-content")
        migration.move_to_private_storage(apps, None)
        self.assertEqual(Path(project.source.path).read_bytes(), b"legacy-content")

    def test_youtube_input_is_optional_exclusive_and_restricted_to_video_links(self):
        from rest_framework.exceptions import ValidationError

        from apps.clips.youtube import youtube_url

        self.assertEqual(
            youtube_url("https://youtu.be/abcdefghijk?t=20"),
            "https://www.youtube.com/watch?v=abcdefghijk",
        )
        self.assertEqual(
            youtube_url("https://www.youtube.com/shorts/abcdefghijk"),
            "https://www.youtube.com/watch?v=abcdefghijk",
        )
        for url in (
            "http://127.0.0.1/watch?v=abcdefghijk",
            "https://youtube.com.evil.test/watch?v=abcdefghijk",
            "https://user@youtube.com/watch?v=abcdefghijk",
            "https://youtube.com:443/watch?v=abcdefghijk",
            "https://youtube.com/playlist?list=abcdefghijk",
        ):
            with self.assertRaises(ValidationError):
                youtube_url(url)
        response = self.client.post(
            reverse("clipproject-list"),
            {"youtube_url": "https://youtu.be/abcdefghijk", "min_duration": 10},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(
            response.data["youtube_url"], "https://www.youtube.com/watch?v=abcdefghijk"
        )
        self.assertIsNone(response.data["source"])
        self.assertEqual(
            self.client.post(
                reverse("clipproject-list"), {}, format="json"
            ).status_code,
            400,
        )
        self.assertEqual(
            self.client.post(
                reverse("clipproject-list"),
                {
                    "source": SimpleUploadedFile("talk.mp4", self.source.read_bytes()),
                    "youtube_url": "https://youtu.be/abcdefghijk",
                    "min_duration": 10,
                },
                format="multipart",
            ).status_code,
            400,
        )

    def test_youtube_download_is_saved_privately_and_reused_after_analysis_failure(
        self,
    ):
        response = self.client.post(
            reverse("clipproject-list"),
            {"youtube_url": "https://youtu.be/abcdefghijk", "min_duration": 10},
            format="json",
        )
        project = ClipProject.objects.get(pk=response.data["id"])
        metadata = {"duration": 20, "width": 160, "height": 90}
        with (
            patch(
                "apps.clips.processing.download_youtube",
                return_value=(self.source, metadata, "Imported interview"),
            ) as download,
            patch("apps.clips.processing.transcribe_audio", return_value=self.words),
            patch(
                "apps.clips.processing.suggest_clips",
                side_effect=RuntimeError("provider"),
            ),
        ):
            process_project(project.pk, project.job_id)
        download.assert_called_once()
        project.refresh_from_db()
        self.assertEqual(project.status, "FAILED")
        self.assertTrue(project.source)
        self.assertEqual(project.title, "Imported interview")
        queue_project(project)
        project.refresh_from_db()
        with (
            patch("apps.clips.processing.download_youtube") as download,
            patch("apps.clips.processing.suggest_clips", return_value=[]),
        ):
            process_project(project.pk, project.job_id)
        download.assert_not_called()
        project.refresh_from_db()
        self.assertEqual(project.status, "READY")

    def test_youtube_import_joins_separate_video_and_audio_streams(self):
        from apps.clips.media import run_ffmpeg
        from apps.clips.youtube import download_youtube

        with tempfile.TemporaryDirectory() as directory:
            picture_path = Path(directory, "picture.mp4")
            audio_path = Path(directory, "audio.m4a")
            run_ffmpeg(
                ["-i", str(self.source), "-an", "-c:v", "copy", str(picture_path)]
            )
            run_ffmpeg(["-i", str(self.source), "-vn", "-c:a", "copy", str(audio_path)])
            picture = MagicMock(
                resolution="1080p", filesize=picture_path.stat().st_size, subtype="mp4"
            )
            picture.download.return_value = str(picture_path)
            audio = MagicMock(filesize=audio_path.stat().st_size, subtype="mp4")
            audio.download.return_value = str(audio_path)
            combined, pictures, sounds = [], [picture], MagicMock()
            sounds.order_by.return_value.desc.return_value.first.return_value = audio
            with patch("apps.clips.youtube.YouTube") as youtube:
                youtube.return_value.length = 20
                youtube.return_value.title = "Separate streams"
                youtube.return_value.streams.filter.side_effect = [
                    combined,
                    pictures,
                    sounds,
                ]
                project = ClipProject(
                    youtube_url="https://youtu.be/abcdefghijk", min_duration=10
                )
                path, metadata, title = download_youtube(project, directory)
            self.assertTrue(path.exists())
            self.assertTrue(metadata["audio"])
            self.assertEqual(metadata["width"], 160)
            self.assertAlmostEqual(metadata["duration"], 20, delta=0.2)
            self.assertEqual(title, "Separate streams")
            picture.download.assert_called_once()
            audio.download.assert_called_once()
