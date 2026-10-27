from unittest.mock import patch

from django.urls import reverse

from ...export_settings import export_settings
from .base import ApiTestCase


class ExportSettingsTests(ApiTestCase):
    def test_saves_export_options_before_dispatch_without_replacing_other_settings(
        self,
    ):
        video = self.video_for(status="READY", settings={"narration": False})

        def dispatched(**kwargs):
            video.refresh_from_db()
            self.assertEqual(video.status, "RENDERING")
            self.assertEqual(
                video.settings,
                {
                    "narration": False,
                    "export_preset": "HIGH",
                    "export_fps": 30,
                },
            )

        with patch(
            "apps.videomanagement.tasks.render_video_task.delay", side_effect=dispatched
        ):
            response = self.client.patch(
                reverse("video-render-video", args=[video.pk]),
                {"export_preset": "HIGH", "export_fps": 30},
                format="json",
            )
        self.assertEqual(response.status_code, 202, response.data)
        self.assertEqual(response.data["video"]["settings"], video.settings)

    def test_empty_render_request_keeps_saved_options(self):
        saved = {"export_preset": "DRAFT", "export_fps": 30}
        video = self.video_for(status="COMPLETED", settings=saved)
        with patch("apps.videomanagement.tasks.render_video_task.delay"):
            response = self.client.patch(reverse("video-render-video", args=[video.pk]))
        self.assertEqual(response.status_code, 202)
        video.refresh_from_db()
        self.assertEqual(video.settings, saved)

    def test_invalid_options_do_not_change_settings_or_queue_a_render(self):
        for payload in (
            {"export_preset": "ULTRA"},
            {"export_fps": 60},
            {"export_fps": 24.5},
            {"export_preset": None},
            {"export_fps": True},
        ):
            with self.subTest(payload=payload):
                video = self.video_for(status="READY", settings={"subtitles": True})
                with patch(
                    "apps.videomanagement.tasks.render_video_task.delay"
                ) as queued:
                    response = self.client.patch(
                        reverse("video-render-video", args=[video.pk]),
                        payload,
                        format="json",
                    )
                self.assertEqual(response.status_code, 400, response.data)
                queued.assert_not_called()
                video.refresh_from_db()
                self.assertEqual(video.status, "READY")
                self.assertEqual(video.settings, {"subtitles": True})

    def test_in_flight_render_does_not_accept_new_options(self):
        video = self.video_for(status="RENDERING", settings={"export_fps": 24})
        with patch("apps.videomanagement.tasks.render_video_task.delay") as queued:
            response = self.client.patch(
                reverse("video-render-video", args=[video.pk]),
                {"export_fps": 30},
                format="json",
            )
        self.assertEqual(response.status_code, 409)
        queued.assert_not_called()
        video.refresh_from_db()
        self.assertEqual(video.settings, {"export_fps": 24})

    def test_legacy_and_invalid_saved_settings_use_standard_defaults(self):
        for saved in (
            {},
            {"export_preset": "missing", "export_fps": 60},
            {"export_preset": [], "export_fps": "30"},
        ):
            self.assertEqual(
                export_settings(saved), {"crf": 23, "preset": "fast", "fps": 24}
            )

    def test_dispatch_failure_preserves_selected_options_for_retry(self):
        video = self.video_for(status="READY")
        with patch(
            "apps.videomanagement.tasks.render_video_task.delay",
            side_effect=RuntimeError("offline"),
        ):
            response = self.client.patch(
                reverse("video-render-video", args=[video.pk]),
                {"export_preset": "HIGH", "export_fps": 30},
                format="json",
            )
        self.assertEqual(response.status_code, 503)
        video.refresh_from_db()
        self.assertEqual(video.status, "READY")
        self.assertEqual(video.settings["export_preset"], "HIGH")
        self.assertEqual(video.settings["export_fps"], 30)

    def test_failed_export_can_be_retried_but_failed_generation_cannot(self):
        for error, expected in (
            ({"message": "Export failed", "reference": "ref"}, 202),
            ({}, 409),
        ):
            with self.subTest(error=error):
                video = self.video_for(status="FAILED", render_error=error)
                with patch(
                    "apps.videomanagement.tasks.render_video_task.delay"
                ) as dispatch:
                    response = self.client.patch(
                        reverse("video-render-video", args=[video.pk])
                    )
                self.assertEqual(response.status_code, expected, response.data)
                self.assertEqual(dispatch.called, expected == 202)

    def test_only_exports_use_the_render_queue(self):
        from video_creator.celery import app

        render = app.amqp.router.route(
            {}, "apps.videomanagement.tasks.render_video_task"
        )
        edit = app.amqp.router.route({}, "apps.videomanagement.tasks.update_scene_task")
        self.assertEqual(render["queue"].name, "renders")
        self.assertEqual(edit["queue"].name, "celery")
