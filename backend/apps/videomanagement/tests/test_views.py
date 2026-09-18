"""End-to-end through the API. Celery is never reached: every .delay is stubbed."""

from unittest.mock import patch

from django.test import TestCase, override_settings
from model_bakery import baker
from rest_framework.test import APIClient

from ..models import SceneImage, Video


class ApiTestCase(TestCase):
    def setUp(self):
        self.user = baker.make_recipe("usermanagement.user")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        # Superusers skip throttling, which is what these tests care about — the rate
        # limits are covered on their own.
        throttle = patch(
            "apps.videomanagement.throttling.BaseThrottle.allow_request",
            return_value=True,
        )
        throttle.start()
        self.addCleanup(throttle.stop)

    def video_for(self, user=None, **kwargs):
        return baker.make_recipe(
            "videomanagement.video", created_by=user or self.user, **kwargs
        )


class GenerateViewTests(ApiTestCase):
    def post(self, **overrides):
        data = {"message": "make me a video about cats"}
        data.update(overrides)
        with patch("apps.videomanagement.tasks.generate_video_task.delay") as delay:
            response = self.client.post("/api/generate/", data)

        return response, delay

    def test_answers_immediately_with_a_video_to_poll(self):
        response, _ = self.post()

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data["video"]["status"], "GENERATION")

    def test_hands_the_work_to_a_worker(self):
        response, delay = self.post(narration=False)

        delay.assert_called_once()
        self.assertEqual(
            delay.call_args.kwargs["video_id"], response.data["video"]["id"]
        )
        self.assertFalse(delay.call_args.kwargs["narration"])

    def test_attributes_the_video_to_the_caller(self):
        response, _ = self.post()

        self.assertEqual(
            Video.objects.get(pk=response.data["video"]["id"]).created_by, self.user
        )

    def test_rejects_a_request_with_no_message(self):
        response, delay = self.post(message="")

        self.assertEqual(response.status_code, 400)
        delay.assert_not_called()

    def test_turns_away_a_user_who_cannot_afford_it(self):
        self.client.force_authenticate(baker.make_recipe("usermanagement.broke_user"))

        response, delay = self.post()

        self.assertEqual(response.status_code, 403)
        delay.assert_not_called()

    def test_turns_away_an_anonymous_visitor(self):
        self.client.force_authenticate(None)

        self.assertEqual(self.post()[0].status_code, 401)


class TwitchGenerateViewTests(ApiTestCase):
    def post(self, **overrides):
        data = {"mode": "game", "value": "Fortnite", "amt": 5}
        data.update(overrides)
        with patch(
            "apps.videomanagement.tasks.generate_twitch_video_task.delay"
        ) as delay:
            response = self.client.post("/api/twitch_generate/", data)

        return response, delay

    def test_answers_immediately_with_a_video_to_poll(self):
        response, delay = self.post()

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data["video"]["video_type"], "TWITCH")
        delay.assert_called_once()

    def test_sends_the_start_date_as_a_day_celery_can_carry(self):
        # Celery's json serializer cannot carry a date, and Twitch wants an ISO day.
        _, delay = self.post(started_at="2026-01-01")

        self.assertEqual(delay.call_args.kwargs["started_at"], "2026-01-01")

    def test_sends_an_empty_window_when_no_date_was_given(self):
        _, delay = self.post()

        self.assertEqual(delay.call_args.kwargs["started_at"], "")

    def test_turns_away_a_user_with_no_twitch_balance(self):
        self.client.force_authenticate(
            baker.make_recipe("usermanagement.user", generation_limit_for_twitch=0)
        )

        self.assertEqual(self.post()[0].status_code, 403)


class VideoViewTests(ApiTestCase):
    def test_lists_only_the_callers_own_videos(self):
        mine = self.video_for()
        self.video_for(user=baker.make_recipe("usermanagement.user"))

        response = self.client.get("/api/video/")

        self.assertEqual([v["id"] for v in response.data["results"]], [mine.id])

    def test_hides_videos_a_worker_has_not_filled_in_yet_from_the_list(self):
        self.video_for(gpt_answer=None)

        self.assertEqual(self.client.get("/api/video/").data["count"], 0)

    def test_still_serves_an_unfilled_video_by_id_so_it_can_be_polled(self):
        video = self.video_for(gpt_answer=None, status="GENERATION")

        response = self.client.get(f"/api/video/{video.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "GENERATION")

    def test_will_not_serve_someone_elses_video(self):
        video = self.video_for(user=baker.make_recipe("usermanagement.user"))

        self.assertEqual(self.client.get(f"/api/video/{video.id}/").status_code, 404)

    def test_filters_by_status(self):
        ready = self.video_for(status="READY")
        self.video_for(status="FAILED")

        response = self.client.get("/api/video/?status=READY")

        self.assertEqual([v["id"] for v in response.data["results"]], [ready.id])

    def test_searches_by_title(self):
        wanted = self.video_for(title="Cats at home")
        self.video_for(title="Dogs at work")

        response = self.client.get("/api/video/?search=Cats")

        self.assertEqual([v["id"] for v in response.data["results"]], [wanted.id])


class VideoUpdateViewTests(ApiTestCase):
    def test_renames_a_video_without_touching_anything_else(self):
        video = self.video_for(title="Old Name")

        response = self.client.patch(
            f"/api/video/{video.id}/", {"title": "New Name"}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        video.refresh_from_db()
        self.assertEqual(video.title, "New Name")

    def test_turns_subtitles_on(self):
        video = self.video_for()

        self.client.patch(
            f"/api/video/{video.id}/",
            {"title": "t", "subtitles": True, "avatar_position": "left,top"},
            format="json",
        )

        video.refresh_from_db()
        self.assertTrue(video.settings["subtitles"])

    def test_will_not_let_a_stranger_update_a_video(self):
        video = self.video_for(user=baker.make_recipe("usermanagement.user"))

        response = self.client.patch(
            f"/api/video/{video.id}/", {"title": "Mine Now"}, format="json"
        )

        self.assertEqual(response.status_code, 404)


class RenderViewTests(ApiTestCase):
    def render(self, video):
        with patch("apps.videomanagement.tasks.render_video_task.delay") as delay:
            response = self.client.patch(f"/api/video/{video.id}/render_video/")

        return response, delay

    def test_queues_the_render_of_a_finished_video(self):
        response, delay = self.render(self.video_for(status="READY"))

        self.assertEqual(response.status_code, 202)
        delay.assert_called_once()

    def test_re_renders_a_video_that_is_already_completed(self):
        response, delay = self.render(self.video_for(status="COMPLETED"))

        self.assertEqual(response.status_code, 202)
        delay.assert_called_once()

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
            response = self.client.patch(f"/api/video/{video.id}/video_regenerate/")

        self.assertEqual(response.status_code, 202)
        delay.assert_called_once_with(video_id=video.id)
        video.refresh_from_db()
        self.assertEqual(video.status, "GENERATION")


class AddSceneViewTests(ApiTestCase):
    def test_adds_a_scene_to_a_video(self):
        video = self.video_for()
        scene = baker.make_recipe("videomanagement.scene", prompt=video.prompt)

        with patch(
            "apps.videomanagement.services.SceneServices.make_scene_speech",
            return_value=scene,
        ):
            response = self.client.post(
                f"/api/video/{video.id}/add_scene/", {"text": "a new line"}
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["scene"]["text"], scene.text)


class SceneViewTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.video = self.video_for()
        self.scene = baker.make_recipe(
            "videomanagement.scene", prompt=self.video.prompt, text="the old line"
        )

    def test_rewrites_a_line_and_charges_for_it(self):
        before = self.user.generation_limit_for_ai

        with patch("apps.videomanagement.services.SceneServices.update"):
            response = self.client.patch(
                f"/api/scene/{self.scene.id}/", {"text": "a new line"}, format="json"
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["text"], "a new line")
        self.user.refresh_from_db()
        self.assertAlmostEqual(self.user.generation_limit_for_ai, before - 0.01)

    def test_asks_the_model_for_a_rewrite_and_charges_more_for_it(self):
        before = self.user.generation_limit_for_ai

        with patch(
            "apps.videomanagement.services.SceneServices.get_update_sentence",
            return_value="a funnier line",
        ):
            response = self.client.patch(
                f"/api/scene/{self.scene.id}/generate/",
                {"text": "make it funnier"},
                format="json",
            )

        self.assertEqual(response.data["text"], "a funnier line")
        self.user.refresh_from_db()
        self.assertAlmostEqual(self.user.generation_limit_for_ai, before - 0.03)

    def test_attaches_an_uploaded_image_to_a_scene_with_none(self):
        response = self.client.post(
            f"/api/scene/{self.scene.id}/change_image_scene/", {"with_audio": False}
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(SceneImage.objects.filter(scene=self.scene).exists())

    def test_replaces_the_visual_of_a_scene_that_has_one(self):
        scene_image = baker.make_recipe(
            "videomanagement.scene_image", scene=self.scene, with_audio=False
        )

        response = self.client.post(
            f"/api/scene/{self.scene.id}/change_image_scene/?scene_image={scene_image.id}",
            {"with_audio": True},
        )

        self.assertEqual(response.status_code, 200)
        scene_image.refresh_from_db()
        self.assertTrue(scene_image.with_audio)

    def test_regenerates_a_scenes_image_and_charges_for_it(self):
        baker.make_recipe("videomanagement.scene_image", scene=self.scene)
        before = self.user.generation_limit_for_ai

        with patch(
            "apps.videomanagement.views.scene_view.generate_new_image"
        ) as generate:
            response = self.client.post(
                f"/api/scene/{self.scene.id}/generate_image_scene/",
                {"image_description": "a cat"},
            )

        self.assertEqual(response.status_code, 200)
        generate.assert_called_once()
        self.user.refresh_from_db()
        self.assertAlmostEqual(self.user.generation_limit_for_ai, before - 0.08)

    def test_will_not_regenerate_an_image_with_nothing_to_go_on(self):
        response = self.client.post(
            f"/api/scene/{self.scene.id}/generate_image_scene/", {}
        )

        self.assertEqual(response.status_code, 400)

    def test_deletes_a_scene(self):
        response = self.client.delete(f"/api/scene/{self.scene.id}/")

        self.assertEqual(response.status_code, 204)
        self.assertFalse(self.video.prompt.scenes.filter(pk=self.scene.pk).exists())

    def test_will_not_touch_a_scene_of_someone_elses_video(self):
        stranger_video = self.video_for(user=baker.make_recipe("usermanagement.user"))
        scene = baker.make_recipe("videomanagement.scene", prompt=stranger_video.prompt)

        self.assertEqual(self.client.delete(f"/api/scene/{scene.id}/").status_code, 403)


class SceneImageViewTests(ApiTestCase):
    def test_clears_the_file_of_an_ai_videos_image_but_keeps_the_scene(self):
        video = self.video_for()
        scene = baker.make_recipe("videomanagement.scene", prompt=video.prompt)
        scene_image = baker.make_recipe("videomanagement.scene_image", scene=scene)

        response = self.client.delete(f"/api/scene_image/{scene_image.id}/")

        self.assertEqual(response.status_code, 204)
        scene_image.refresh_from_db()
        self.assertFalse(scene_image.file)

    def test_removes_the_whole_scene_of_a_twitch_video(self):
        # The clip is the scene, so an empty one would render as a black gap.
        video = self.video_for(video_type="TWITCH")
        scene = baker.make_recipe("videomanagement.scene", prompt=video.prompt)
        scene_image = baker.make_recipe("videomanagement.scene_image", scene=scene)

        self.client.delete(f"/api/scene_image/{scene_image.id}/")

        self.assertFalse(video.prompt.scenes.filter(pk=scene.pk).exists())


class LibraryViewTests(ApiTestCase):
    """Intros, outros, avatars and voices a caller can pick from."""

    def test_each_owner_sees_only_their_own_intros_and_outros(self):
        mine = baker.make_recipe("videomanagement.intro", created_by=self.user)
        baker.make_recipe(
            "videomanagement.intro",
            created_by=baker.make_recipe("usermanagement.user"),
        )

        response = self.client.get("/api/intro/")

        self.assertEqual([i["id"] for i in response.data], [mine.id])

    def test_a_superuser_sees_every_intro(self):
        baker.make_recipe("videomanagement.intro", _quantity=2)
        self.client.force_authenticate(baker.make_recipe("usermanagement.superuser"))

        self.assertEqual(len(self.client.get("/api/intro/").data), 2)

    def test_each_owner_sees_only_their_own_avatars(self):
        mine = baker.make_recipe("videomanagement.avatar", created_by=self.user)
        baker.make_recipe("videomanagement.avatar")

        response = self.client.get("/api/avatars/")

        self.assertEqual([a["id"] for a in response.data], [mine.id])

    @override_settings(OPEN_API_KEY="service-openai")
    def test_voices_are_shared_by_everyone(self):
        baker.make_recipe("videomanagement.voice_model", _quantity=2)

        self.assertEqual(len(self.client.get("/api/voices/").data), 2)

    def test_no_voices_are_offered_when_no_key_reaches_their_provider(self):
        baker.make_recipe("videomanagement.voice_model", _quantity=2)

        self.assertEqual(len(self.client.get("/api/voices/").data), 0)
