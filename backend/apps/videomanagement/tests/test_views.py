"""End-to-end through the API. Celery is never reached: every .delay is stubbed."""

from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.usermanagement.baker_recipes import broke_user, superuser, user

from ..baker_recipes import avatar, intro, scene, scene_image, video, voice_model
from ..models import SceneImage, Video


class ApiTestCase(TestCase):
    def setUp(self):
        self.user = user.make()
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

    def video_for(self, owner=None, **kwargs):
        return video.make(created_by=owner or self.user, **kwargs)


class GenerateViewTests(ApiTestCase):
    def post(self, **overrides):
        data = {"message": "make me a video about cats"}
        data.update(overrides)
        with patch("apps.videomanagement.tasks.generate_video_task.delay") as delay:
            response = self.client.post(reverse("generate"), data)

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
        self.client.force_authenticate(broke_user.make())

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
            response = self.client.post(reverse("twitch_generate"), data)

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
        self.client.force_authenticate(user.make(generation_limit_for_twitch=0))

        self.assertEqual(self.post()[0].status_code, 403)


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
        # A client that polls straight after the 202 would otherwise read the status
        # left by the last render and call this render finished before it started.
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


class SceneViewTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.video = self.video_for()
        self.scene = scene.make(prompt=self.video.prompt, text="the old line")

    def test_rewrites_a_line_and_charges_for_it(self):
        before = self.user.generation_limit_for_ai

        with patch("apps.videomanagement.services.SceneServices.update"):
            response = self.client.patch(
                reverse("scene-detail", args=[self.scene.id]),
                {"text": "a new line"},
                format="json",
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
                reverse("scene-generate", args=[self.scene.id]),
                {"text": "make it funnier"},
                format="json",
            )

        self.assertEqual(response.data["text"], "a funnier line")
        self.user.refresh_from_db()
        self.assertAlmostEqual(self.user.generation_limit_for_ai, before - 0.03)

    def test_attaches_an_uploaded_image_to_a_scene_with_none(self):
        response = self.client.post(
            reverse("scene-change-image-scene", args=[self.scene.id]),
            {"with_audio": False},
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(SceneImage.objects.filter(scene=self.scene).exists())

    def test_replaces_the_visual_of_a_scene_that_has_one(self):
        image = scene_image.make(scene=self.scene, with_audio=False)

        response = self.client.post(
            f"{reverse('scene-change-image-scene', args=[self.scene.id])}"
            f"?scene_image={image.id}",
            {"with_audio": True},
        )

        self.assertEqual(response.status_code, 200)
        image.refresh_from_db()
        self.assertTrue(image.with_audio)

    def test_regenerates_a_scenes_image_and_charges_for_it(self):
        scene_image.make(scene=self.scene)
        before = self.user.generation_limit_for_ai

        with patch(
            "apps.videomanagement.views.scene_view.generate_new_image"
        ) as generate:
            response = self.client.post(
                reverse("scene-generate-image-scene", args=[self.scene.id]),
                {"image_description": "a cat"},
            )

        self.assertEqual(response.status_code, 200)
        generate.assert_called_once()
        self.user.refresh_from_db()
        self.assertAlmostEqual(self.user.generation_limit_for_ai, before - 0.08)

    def test_will_not_regenerate_an_image_with_nothing_to_go_on(self):
        response = self.client.post(
            reverse("scene-generate-image-scene", args=[self.scene.id]), {}
        )

        self.assertEqual(response.status_code, 400)

    def test_deletes_a_scene(self):
        response = self.client.delete(reverse("scene-detail", args=[self.scene.id]))

        self.assertEqual(response.status_code, 204)
        self.assertFalse(self.video.prompt.scenes.filter(pk=self.scene.pk).exists())

    def test_will_not_touch_a_scene_of_someone_elses_video(self):
        stranger_video = self.video_for(owner=user.make())
        theirs = scene.make(prompt=stranger_video.prompt)

        response = self.client.delete(reverse("scene-detail", args=[theirs.id]))

        self.assertEqual(response.status_code, 403)


class SceneImageViewTests(ApiTestCase):
    def test_clears_the_file_of_an_ai_videos_image_but_keeps_the_scene(self):
        video_row = self.video_for()
        line = scene.make(prompt=video_row.prompt)
        image = scene_image.make(scene=line)

        response = self.client.delete(reverse("sceneimage-detail", args=[image.id]))

        self.assertEqual(response.status_code, 204)
        image.refresh_from_db()
        self.assertFalse(image.file)

    def test_removes_the_whole_scene_of_a_twitch_video(self):
        # The clip is the scene, so an empty one would render as a black gap.
        video_row = self.video_for(video_type="TWITCH")
        clip = scene.make(prompt=video_row.prompt)
        image = scene_image.make(scene=clip)

        self.client.delete(reverse("sceneimage-detail", args=[image.id]))

        self.assertFalse(video_row.prompt.scenes.filter(pk=clip.pk).exists())


class LibraryViewTests(ApiTestCase):
    """Intros, outros, avatars and voices a caller can pick from."""

    def test_each_owner_sees_only_their_own_intros_and_outros(self):
        mine = intro.make(created_by=self.user)
        intro.make(
            created_by=user.make(),
        )

        response = self.client.get(reverse("intro-list"))

        self.assertEqual([i["id"] for i in response.data], [mine.id])

    def test_a_superuser_sees_every_intro(self):
        intro.make(_quantity=2)
        self.client.force_authenticate(superuser.make())

        self.assertEqual(len(self.client.get(reverse("intro-list")).data), 2)

    def test_each_owner_sees_only_their_own_avatars(self):
        mine = avatar.make(created_by=self.user)
        avatar.make()

        response = self.client.get(reverse("avatar-list"))

        self.assertEqual([a["id"] for a in response.data], [mine.id])

    def test_voices_are_shared_by_everyone(self):
        voice_model.make(_quantity=2)

        self.assertEqual(len(self.client.get(reverse("voicemodel-list")).data), 2)

    @override_settings(OPEN_API_KEY="")
    def test_no_voices_are_offered_when_no_key_reaches_their_provider(self):
        voice_model.make(_quantity=2)

        self.assertEqual(len(self.client.get(reverse("voicemodel-list")).data), 0)
