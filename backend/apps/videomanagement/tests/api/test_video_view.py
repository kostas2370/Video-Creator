from unittest.mock import patch

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework.test import APIClient

from apps.usermanagement.baker_recipes import broke_user, user

from ...baker_recipes import avatar, intro, outro, scene, scene_image, video
from .base import ApiTestCase


class VideoDetailQueryTests(TestCase):
    def setUp(self):
        self.user = user.make()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def queries_for(self, scene_count):
        detailed = video.make(created_by=self.user)
        for line in scene.make(video=detailed, _quantity=scene_count):
            scene_image.make(scene=line)

        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(reverse("video-detail", args=[detailed.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["scenes"]), scene_count)

        return len(queries)

    def test_costs_the_same_whether_a_video_has_two_scenes_or_twenty(self):
        self.assertEqual(self.queries_for(2), self.queries_for(20))


class VideoViewTests(ApiTestCase):
    def test_unsupported_write_routes_return_405_without_mutating_videos(self):
        row = self.video_for(title="Original")
        payload = {"title": "Changed", "prompt": {"prompt": "New prompt"}}
        count = row.__class__.objects.count()
        response = self.client.post(reverse("video-list"), payload, format="json")
        self.assertEqual(response.status_code, 405)
        response = self.client.put(
            reverse("video-detail", args=[row.pk]), payload, format="json"
        )
        self.assertEqual(response.status_code, 405)
        self.assertEqual(row.__class__.objects.count(), count)
        row.refresh_from_db()
        self.assertEqual(row.title, "Original")

    def test_lists_only_the_callers_own_videos(self):
        mine = self.video_for()
        self.video_for(owner=user.make())

        response = self.client.get(reverse("video-list"))

        self.assertEqual([v["id"] for v in response.data["results"]], [mine.id])

    def test_hides_videos_a_worker_has_not_filled_in_yet_from_the_list(self):
        self.video_for(gpt_answer=None)

        self.assertEqual(self.client.get(reverse("video-list")).data["count"], 0)

    def test_still_serves_an_unfilled_video_by_id_so_it_can_be_polled(self):
        video = self.video_for(gpt_answer=None, status="GENERATION")

        response = self.client.get(reverse("video-detail", args=[video.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "GENERATION")

    def test_will_not_serve_someone_elses_video(self):
        video = self.video_for(owner=user.make())

        self.assertEqual(
            self.client.get(reverse("video-detail", args=[video.id])).status_code, 404
        )

    def test_filters_by_status(self):
        ready = self.video_for(status="READY")
        self.video_for(status="FAILED")

        response = self.client.get(f"{reverse('video-list')}?status=READY")

        self.assertEqual([v["id"] for v in response.data["results"]], [ready.id])

    def test_searches_by_title(self):
        wanted = self.video_for(title="Cats at home")
        self.video_for(title="Dogs at work")

        response = self.client.get(f"{reverse('video-list')}?search=Cats")

        self.assertEqual([v["id"] for v in response.data["results"]], [wanted.id])


class VideoUpdateViewTests(ApiTestCase):
    def test_renames_a_video_without_touching_anything_else(self):
        selected_avatar = avatar.make(created_by=self.user)
        opening = intro.make(created_by=self.user)
        closing = outro.make(created_by=self.user)
        original_settings = {
            "narration": False, "subtitles": True, "avatar_position": "left,bottom"
        }
        video = self.video_for(
            title="Old Name", avatar=selected_avatar, intro=opening, outro=closing,
            settings=original_settings,
        )
        original_voice = video.voice_model_id

        response = self.client.patch(
            reverse("video-detail", args=[video.id]),
            {"title": "New Name"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        video.refresh_from_db()
        self.assertEqual(video.title, "New Name")
        self.assertEqual(video.avatar_id, selected_avatar.pk)
        self.assertEqual(video.intro_id, opening.pk)
        self.assertEqual(video.outro_id, closing.pk)
        self.assertEqual(video.voice_model_id, original_voice)
        self.assertEqual(video.settings, original_settings)

    def test_explicit_null_clears_only_the_selected_asset(self):
        opening = intro.make(created_by=self.user)
        closing = outro.make(created_by=self.user)
        row = self.video_for(intro=opening, outro=closing)
        response = self.client.patch(
            reverse("video-detail", args=[row.pk]), {"intro": None}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        row.refresh_from_db()
        self.assertIsNone(row.intro_id)
        self.assertEqual(row.outro_id, closing.pk)

    def test_turns_subtitles_on(self):
        video = self.video_for()

        self.client.patch(
            reverse("video-detail", args=[video.id]),
            {"title": "t", "subtitles": True, "avatar_position": "left,top"},
            format="json",
        )

        video.refresh_from_db()
        self.assertTrue(video.settings["subtitles"])

    def test_will_not_let_a_stranger_update_a_video(self):
        video = self.video_for(owner=user.make())

        response = self.client.patch(
            reverse("video-detail", args=[video.id]),
            {"title": "Mine Now"},
            format="json",
        )

        self.assertEqual(response.status_code, 404)

    def test_rejects_foreign_assets_before_changing_the_video(self):
        row = self.video_for(title="Original")
        for field, recipe in (("avatar", avatar), ("intro", intro), ("outro", outro)):
            with self.subTest(field=field):
                asset = recipe.make(created_by=user.make())
                with patch("apps.videomanagement.services.VideoServices.update_scene") as regenerate:
                    response = self.client.patch(
                        reverse("video-detail", args=[row.id]),
                        {"title": "Changed", field: str(asset.id)},
                        format="json",
                    )
                self.assertEqual(response.status_code, 404)
                regenerate.assert_not_called()
                row.refresh_from_db()
                self.assertEqual(row.title, "Original")

    def test_accepts_owned_intro_and_outro(self):
        row = self.video_for()
        opening = intro.make(created_by=self.user)
        closing = outro.make(created_by=self.user)
        response = self.client.patch(
            reverse("video-detail", args=[row.id]),
            {"intro": str(opening.id), "outro": str(closing.id)},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        row.refresh_from_db()
        self.assertEqual(row.intro, opening)
        self.assertEqual(row.outro, closing)


class RenderViewTests(ApiTestCase):
    def render(self, video):
        with patch("apps.videomanagement.tasks.render_video_task.delay") as delay:
            response = self.client.patch(reverse("video-render-video", args=[video.id]))

        return response, delay

    def test_queues_the_render_of_a_finished_video(self):
        response, delay = self.render(self.video_for(status="READY"))

        self.assertEqual(response.status_code, 202)
        delay.assert_called_once()

    def test_re_renders_a_video_that_is_already_completed(self):
        response, delay = self.render(self.video_for(status="COMPLETED"))

        self.assertEqual(response.status_code, 202)
        delay.assert_called_once()

    def test_marks_the_video_rendering_before_the_worker_picks_it_up(self):
        rendered = self.video_for(status="COMPLETED")

        response, _ = self.render(rendered)

        rendered.refresh_from_db()
        self.assertEqual(rendered.status, "RENDERING")
        self.assertEqual(response.data["video"]["status"], "RENDERING")

    def test_refuses_a_second_render_while_the_first_is_still_queued(self):
        rendered = self.video_for(status="COMPLETED")
        self.render(rendered)

        response, delay = self.render(rendered)

        self.assertEqual(response.status_code, 409)
        delay.assert_not_called()

    def test_refuses_to_render_a_video_a_worker_has_not_finished(self):
        for status in ("GENERATION", "RENDERING", "FAILED"):
            with self.subTest(status=status):
                response, delay = self.render(self.video_for(status=status))

                self.assertEqual(response.status_code, 409)
                delay.assert_not_called()


class AddSceneViewTests(ApiTestCase):
    def test_queues_a_reviewed_section_as_one_job(self):
        row = self.video_for()
        scenes = [{"text": "First sentence."}, {"text": "Second sentence.", "is_last": True}]
        with patch("apps.videomanagement.views.video_view.create_scene_task.delay") as delay:
            response = self.client.post(reverse("video-add-scene", args=[row.pk]), {"scenes": scenes}, format="json")
        self.assertEqual(response.status_code, 202)
        queued = delay.call_args.args[1]["scenes"]
        self.assertEqual([item["text"] for item in queued], [item["text"] for item in scenes])
        self.assertFalse(queued[0]["is_last"])
        self.assertTrue(queued[1]["is_last"])
        self.assertFalse(row.scenes.exists())

    def test_validates_every_sentence_before_claiming_a_batch(self):
        row = self.video_for()
        for scenes in ([], [{"text": "Valid"}, {"text": " "}], [{"text": "A line"}] * 13):
            with self.subTest(scenes=scenes), patch("apps.videomanagement.views.video_view.create_scene_task.delay") as delay:
                response = self.client.post(reverse("video-add-scene", args=[row.pk]), {"scenes": scenes}, format="json")
            self.assertEqual(response.status_code, 400)
            delay.assert_not_called()
        row.refresh_from_db()
        self.assertEqual(row.status, "READY")

    def test_queues_without_running_providers_and_persists_progress(self):
        row = self.video_for()
        with patch("apps.videomanagement.views.video_view.create_scene_task.delay") as delay:
            response = self.client.post(reverse("video-add-scene", args=[row.pk]), {"text": "New line"})
        self.assertEqual(response.status_code, 202)
        self.assertEqual(delay.call_args.args[0], row.pk)
        self.assertEqual(delay.call_args.args[1]["text"], "New line")
        self.assertIsNone(delay.call_args.args[2])
        self.assertFalse(row.scenes.exists())
        row.refresh_from_db()
        self.assertEqual(row.status, "GENERATION")
        detail = self.client.get(reverse("video-detail", args=[row.pk]))
        self.assertEqual(detail.data["status"], "GENERATION")

    def test_rejects_invalid_input_before_queueing(self):
        row = self.video_for()
        with patch("apps.videomanagement.views.video_view.create_scene_task.delay") as delay:
            response = self.client.post(reverse("video-add-scene", args=[row.pk]), {"text": " "})
        self.assertEqual(response.status_code, 400)
        delay.assert_not_called()
        row.refresh_from_db()
        self.assertEqual(row.status, "READY")

    def test_duplicate_submission_and_render_are_blocked_until_done(self):
        row = self.video_for()
        with patch("apps.videomanagement.views.video_view.create_scene_task.delay") as delay:
            url = reverse("video-add-scene", args=[row.pk])
            self.client.post(url, {"text": "New line"})
            response = self.client.post(url, {"text": "New line"})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(delay.call_count, 1)
        with patch("apps.videomanagement.views.video_view.render_video_task.delay") as render:
            response = self.client.patch(reverse("video-render-video", args=[row.pk]))
        self.assertEqual(response.status_code, 409)
        render.assert_not_called()

    def test_queue_failure_restores_video_and_returns_retryable_error(self):
        row = self.video_for(status="COMPLETED")
        with patch("apps.videomanagement.views.video_view.create_scene_task.delay", side_effect=RuntimeError("offline")):
            response = self.client.post(reverse("video-add-scene", args=[row.pk]), {"text": "New line"})
        self.assertEqual(response.status_code, 503)
        row.refresh_from_db()
        self.assertEqual(row.status, "COMPLETED")

    def test_cannot_queue_for_another_users_video(self):
        row = self.video_for(owner=user.make())
        with patch("apps.videomanagement.views.video_view.create_scene_task.delay") as delay:
            response = self.client.post(reverse("video-add-scene", args=[row.pk]), {"text": "New line"})
        self.assertEqual(response.status_code, 404)
        delay.assert_not_called()


class ResumeViewTests(ApiTestCase):
    def resume(self, video):
        with patch("apps.videomanagement.tasks.resume_video_task.delay") as delay:
            response = self.client.patch(reverse("video-resume", args=[video.id]))

        return response, delay

    def a_failed_video(self, **kwargs):
        return self.video_for(
            status="FAILED",
            gpt_answer={"title": "Cats", "scenes": []},
            dir_name="media/videos/cats",
            **kwargs,
        )

    def test_carries_on_a_generation_that_stopped_early(self):
        stalled = self.a_failed_video()

        response, delay = self.resume(stalled)

        self.assertEqual(response.status_code, 202)
        delay.assert_called_once()

    def test_marks_it_generating_before_the_worker_picks_it_up(self):
        stalled = self.a_failed_video()

        self.resume(stalled)

        stalled.refresh_from_db()
        self.assertEqual(stalled.status, "GENERATION")

    def test_refuses_a_video_that_never_got_a_script(self):
        empty = self.video_for(status="FAILED", gpt_answer=None)

        response, delay = self.resume(empty)

        self.assertEqual(response.status_code, 409)
        delay.assert_not_called()

    def test_refuses_a_video_a_worker_is_still_on(self):
        for status_name in ("GENERATION", "RENDERING"):
            with self.subTest(status=status_name):
                busy = self.a_failed_video()
                busy.status = status_name
                busy.save()

                response, delay = self.resume(busy)

                self.assertEqual(response.status_code, 409)
                delay.assert_not_called()

    def test_a_stranger_cannot_resume_it(self):
        theirs = self.a_failed_video(owner=user.make())

        response, delay = self.resume(theirs)

        self.assertEqual(response.status_code, 404)
        delay.assert_not_called()

    def test_refuses_someone_who_has_spent_their_allowance(self):
        broke = broke_user.make()
        stalled = self.a_failed_video(owner=broke)
        self.client.force_authenticate(broke)

        response, delay = self.resume(stalled)

        self.assertEqual(response.status_code, 403)
        delay.assert_not_called()


class SceneDraftApiTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.video = self.video_for()
        self.url = reverse("video-draft-scene", args=[self.video.pk])

    def test_draft_is_reviewable_without_saving_and_charges_credit(self):
        before = self.user.generation_limit_for_ai
        draft = {"text": "Next scene", "image_description": "The road ahead"}
        with patch("apps.videomanagement.views.video_view.draft_scene", return_value=draft) as generate:
            response = self.client.post(self.url, {"prompt": "Continue", "use_context": True}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, draft)
        self.assertTrue(generate.call_args.kwargs["use_context"])
        self.assertFalse(self.video.scenes.exists())
        self.user.refresh_from_db()
        self.assertAlmostEqual(self.user.generation_limit_for_ai, before - 0.03)

    def test_invalid_inputs_do_not_generate_or_charge(self):
        before = self.user.generation_limit_for_ai
        for data in ({}, {"prompt": " "}, {"prompt": "x" * 2001}, {"prompt": "Next", "use_context": "invalid"}):
            with self.subTest(data=data), patch("apps.videomanagement.views.video_view.draft_scene") as generate:
                response = self.client.post(self.url, data, format="json")
            self.assertEqual(response.status_code, 400)
            generate.assert_not_called()
        self.user.refresh_from_db()
        self.assertEqual(self.user.generation_limit_for_ai, before)

    def test_other_users_cannot_request_scenario_context(self):
        other = self.video_for(owner=user.make())
        with patch("apps.videomanagement.views.video_view.draft_scene") as generate:
            response = self.client.post(reverse("video-draft-scene", args=[other.pk]), {"prompt": "Next", "use_context": True}, format="json")
        self.assertEqual(response.status_code, 404)
        generate.assert_not_called()

    def test_provider_failure_refunds_credit(self):
        from rest_framework.exceptions import APIException

        before = self.user.generation_limit_for_ai
        with patch("apps.videomanagement.views.video_view.draft_scene", side_effect=APIException("Unavailable")):
            response = self.client.post(self.url, {"prompt": "Next"}, format="json")
        self.assertEqual(response.status_code, 500)
        self.user.refresh_from_db()
        self.assertEqual(self.user.generation_limit_for_ai, before)

    def test_insufficient_credit_does_not_call_provider(self):
        self.user.generation_limit_for_ai = 0
        self.user.save()
        with patch("apps.videomanagement.views.video_view.draft_scene") as generate:
            response = self.client.post(self.url, {"prompt": "Next"}, format="json")
        self.assertEqual(response.status_code, 403)
        generate.assert_not_called()
