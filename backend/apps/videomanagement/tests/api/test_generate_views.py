from unittest.mock import patch

from django.test import override_settings
from django.urls import reverse

from apps.usermanagement.baker_recipes import broke_user, user

from ...models import Video
from ...baker_recipes import avatar, intro, outro, voice_model
from .base import ApiTestCase


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

    def test_json_generation_accepts_blank_optional_music_audience_and_genre(self):
        for music in ("", "   ", None):
            with self.subTest(music=music):
                with patch(
                    "apps.videomanagement.tasks.generate_video_task.delay"
                ) as delay:
                    response = self.client.post(
                        reverse("generate"),
                        {
                            "message": "A video without background music",
                            "music": music,
                            "target_audience": "",
                            "genre": "",
                        },
                        format="json",
                    )
                self.assertEqual(response.status_code, 202, response.data)
                delay.assert_called_once()
                self.assertIn(delay.call_args.kwargs["music"], ("", None))

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

    def test_rejects_foreign_assets_without_creating_or_queueing_a_video(self):
        for field, recipe in (("avatar_selection", avatar), ("intro", intro), ("outro", outro)):
            with self.subTest(field=field):
                asset = recipe.make(created_by=user.make())
                count = Video.objects.count()
                response, delay = self.post(**{field: str(asset.id)})
                self.assertEqual(response.status_code, 404)
                self.assertEqual(Video.objects.count(), count)
                delay.assert_not_called()

    def test_accepts_owned_assets(self):
        response, delay = self.post(
            avatar_selection=str(avatar.make(created_by=self.user).id),
            intro=str(intro.make(created_by=self.user).id),
            outro=str(outro.make(created_by=self.user).id),
        )
        self.assertEqual(response.status_code, 202)
        delay.assert_called_once()

    def test_rejects_a_foreign_private_voice_before_queueing(self):
        foreign = voice_model.make(created_by=user.make(), type="CUSTOM_API", provider="private")
        count = Video.objects.count()
        response, delay = self.post(voice_id=str(foreign.id))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Video.objects.count(), count)
        delay.assert_not_called()


@override_settings(TWITCH_GENERATION_ENABLED=True)
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


class DisabledTwitchGenerateViewTests(ApiTestCase):
    @override_settings(TWITCH_GENERATION_ENABLED=False)
    def test_rejects_generation_without_creating_a_video_or_queueing_work(self):
        count = Video.objects.count()
        with patch(
            "apps.videomanagement.tasks.generate_twitch_video_task.delay"
        ) as delay:
            response = self.client.post(
                reverse("twitch_generate"),
                {"mode": "game", "value": "Fortnite", "amt": 5},
            )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(Video.objects.count(), count)
        delay.assert_not_called()
