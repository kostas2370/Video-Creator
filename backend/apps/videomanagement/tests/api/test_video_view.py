from unittest.mock import patch

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework.test import APIClient

from apps.usermanagement.baker_recipes import user

from ...baker_recipes import scene, scene_image, video
from .base import ApiTestCase


class VideoDetailQueryTests(TestCase):
    def setUp(self):
        self.user = user.make()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def queries_for(self, scene_count):
        detailed = video.make(created_by=self.user)
        for line in scene.make(prompt=detailed.prompt, _quantity=scene_count):
            scene_image.make(scene=line)

        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(reverse("video-detail", args=[detailed.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["scenes"]), scene_count)

        return len(queries)

    def test_costs_the_same_whether_a_video_has_two_scenes_or_twenty(self):
        self.assertEqual(self.queries_for(2), self.queries_for(20))


class VideoViewTests(ApiTestCase):
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
        video = self.video_for(title="Old Name")

        response = self.client.patch(
            reverse("video-detail", args=[video.id]),
            {"title": "New Name"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        video.refresh_from_db()
        self.assertEqual(video.title, "New Name")

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


class RegenerateViewTests(ApiTestCase):
    def test_queues_regeneration_and_moves_the_video_back_to_generation(self):
        video = self.video_for(status="COMPLETED")

        with patch("apps.videomanagement.tasks.regenerate_video_task.delay") as delay:
            response = self.client.patch(
                reverse("video-video-regenerate", args=[video.id])
            )

        self.assertEqual(response.status_code, 202)
        delay.assert_called_once_with(video_id=video.id)
        video.refresh_from_db()
        self.assertEqual(video.status, "GENERATION")


class AddSceneViewTests(ApiTestCase):
    def test_adds_a_scene_to_a_video(self):
        video_row = self.video_for()
        added = scene.make(prompt=video_row.prompt)

        with patch(
            "apps.videomanagement.services.SceneServices.make_scene_speech",
            return_value=added,
        ):
            response = self.client.post(
                reverse("video-add-scene", args=[video_row.id]), {"text": "a new line"}
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["scene"]["text"], added.text)


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
