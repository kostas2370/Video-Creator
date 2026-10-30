"""Generation, with the model, TTS and imagery all stubbed."""

from unittest.mock import patch

from django.test import TestCase
from rest_framework.exceptions import APIException

from apps.apikeysmanagement.models import UserCustomVisualProvider
from apps.usermanagement.baker_recipes import user
from apps.videomanagement.baker_recipes import avatar, intro, outro, video, voice_model
from apps.videomanagement.services.videos import generation as VideoGenerationServices
from apps.videomanagement.services.videos.generation import (
    create_pending_video,
    generate_video,
    resume_video,
)

A_SCRIPT = {
    "title": "Cats and how they nap",
    "scenes": [
        {
            "scene": "one",
            "sentences": [{"sentence": "hello", "image_description": "a cat"}],
        }
    ],
}


class CreatePendingVideoTests(TestCase):
    """The only part of generation cheap enough to run inside a request."""

    def setUp(self):
        self.user = user.make()

    def test_hands_back_a_video_the_client_can_poll_immediately(self):
        video = create_pending_video("make me a video", created_by=self.user)

        self.assertEqual(video.status, "GENERATION")
        self.assertIsNone(video.gpt_answer)
        self.assertEqual(video.created_by, self.user)

    def test_stores_the_message_as_the_prompt(self):
        video = create_pending_video("make me a video", created_by=self.user)

        self.assertEqual(video.prompt.prompt, "make me a video")

    def test_trims_a_long_message_to_fit_the_title(self):
        video = create_pending_video("x" * 200, created_by=self.user)

        self.assertEqual(len(video.title), 50)

    def test_prefers_an_explicit_title(self):
        video = create_pending_video(
            "gaming", created_by=self.user, title="Fortnite 2026"
        )

        self.assertEqual(video.title, "Fortnite 2026")
        self.assertEqual(video.video_type, "AI")


class GenerateVideoTests(TestCase):
    def setUp(self):
        self.user = user.make()
        self.voice = voice_model.make()
        self.video = create_pending_video("cats", created_by=self.user)

        for name, value in (
            ("get_reply", A_SCRIPT),
            ("generate_directory", "media/videos/cats"),
            ("make_scenes_speech", None),
            ("create_image_scenes", None),
            ("download_music", None),
        ):
            patcher = patch.object(VideoGenerationServices, name, return_value=value)
            setattr(self, name, patcher.start())
            self.addCleanup(patcher.stop)

    def generate(self, **kwargs):
        params = dict(
            genre="",
            message="cats",
            gpt_model="gpt-4",
            image_mode="WEB",
            avatar_selection="",
            style="vivid",
            target_audience="",
            voice_id=self.voice.id,
        )
        params.update(kwargs)
        return generate_video(video=self.video, **params)

    def test_music_download_uses_the_video_owner(self):
        url = "https://youtu.be/abcdefghijk"
        self.generate(music=url)
        self.download_music.assert_called_once_with(url, user=self.user)

    def test_review_stops_before_media_and_uses_approved_script_on_proceed(self):
        self.video.settings = {"generation_params": {"message": "cats", "review_script": False}}
        self.video.save()
        draft = self.generate(review_script=True)
        self.assertEqual(draft.status, "REVIEW")
        self.assertEqual(draft.settings["generation_params"]["message"], "cats")
        self.make_scenes_speech.assert_not_called()
        self.create_image_scenes.assert_not_called()
        self.download_music.assert_not_called()
        self.assertEqual(draft.scenes.count(), 0)
        draft.gpt_answer = {**A_SCRIPT, "title": "Edited title"}
        draft.save()
        finished = self.generate()
        self.assertEqual(finished.status, "READY")
        self.assertEqual(finished.title, "Edited title")
        self.get_reply.assert_called_once()
        self.make_scenes_speech.assert_called_once()
        self.create_image_scenes.assert_called_once()

    def test_uploaded_image_is_analyzed_with_preferences_and_reference_role(self):
        brief = "Orange fox with the requested blue scarf; watercolor style."
        self.get_reply.return_value = {**A_SCRIPT, "visual_continuity": brief}
        self.video.reference_image = "media/reference.png"
        self.video.save()
        made = self.generate(
            image_mode="AI", visual_continuity="Use a blue scarf", reference_role="character", review_script=True,
        )
        self.assertEqual(self.get_reply.call_args.kwargs["reference_image"], self.video.reference_image.path)
        self.assertIn("Extract only visible subject identity", self.get_reply.call_args.args[0])
        self.assertIn("Use a blue scarf", self.get_reply.call_args.args[0])
        self.assertEqual(made.settings["visual_continuity"], brief)
        self.assertEqual(made.settings["reference_role"], "character")

    def test_empty_image_analysis_draft_keeps_explicit_user_preferences(self):
        self.get_reply.return_value = {**A_SCRIPT, "visual_continuity": ""}
        self.video.reference_image = "media/reference.png"
        self.video.save()
        made = self.generate(image_mode="AI", visual_continuity="Keep the blue scarf", review_script=True)
        self.assertEqual(made.settings["visual_continuity"], "Keep the blue scarf")

    def test_approved_reference_storyboard_does_not_request_image_analysis_again(self):
        self.video.reference_image = "media/reference.png"
        self.video.gpt_answer = {**A_SCRIPT, "visual_continuity": "Reviewed description"}
        self.video.dir_name = "media/videos/cats"
        self.video.save()
        made = self.generate(image_mode="AI", visual_continuity="Reviewed description", reference_role="style")
        self.get_reply.assert_not_called()
        self.assertEqual(made.settings["visual_continuity"], "Reviewed description")
        self.assertEqual(made.settings["reference_role"], "style")

    def test_ai_drafts_and_saves_continuity_in_the_storyboard_request(self):
        brief = "Orange fox Milo, green scarf; watercolor forest."
        self.get_reply.return_value = {**A_SCRIPT, "visual_continuity": brief}
        self.video.settings = {"generation_params": {"image_mode": "AI", "review_script": False}}
        self.video.save()
        made = self.generate(image_mode="AI", review_script=True)
        self.assertEqual(made.settings["visual_continuity"], brief)
        self.assertEqual(made.gpt_answer["visual_continuity"], brief)
        self.assertEqual(made.settings["generation_params"]["visual_continuity"], brief)
        self.assertTrue(self.get_reply.call_args.kwargs["require_visual_continuity"])
        self.get_reply.assert_called_once()
        self.create_image_scenes.assert_not_called()

    def test_user_description_wins_over_ai_draft_and_reaches_visuals(self):
        self.get_reply.return_value = {**A_SCRIPT, "visual_continuity": "AI draft"}
        made = self.generate(image_mode="AI", visual_continuity="My exact character")
        self.assertEqual(made.settings["visual_continuity"], "My exact character")
        self.assertEqual(made.gpt_answer["visual_continuity"], "My exact character")
        self.assertEqual(self.create_image_scenes.call_args.args[0].settings["visual_continuity"], "My exact character")

    def test_reviewed_blank_continuity_stays_cleared_when_media_generation_starts(self):
        self.video.gpt_answer = {**A_SCRIPT, "visual_continuity": ""}
        self.video.dir_name = "media/videos/cats"
        self.video.settings = {"visual_continuity": "Old AI draft"}
        self.video.save()
        made = self.generate(image_mode="AI", visual_continuity="")
        self.assertFalse(made.settings.get("visual_continuity"))
        self.assertEqual(made.gpt_answer["visual_continuity"], "")
        self.get_reply.assert_not_called()

    def test_web_generation_does_not_request_or_apply_ai_character_draft(self):
        self.get_reply.return_value = {**A_SCRIPT, "visual_continuity": "Unexpected AI draft"}
        made = self.generate(image_mode="WEB")
        self.assertNotIn("visual_continuity", made.settings)
        self.assertFalse(self.get_reply.call_args.kwargs["require_visual_continuity"])

    def test_shared_continuity_survives_review_and_reaches_storyboard(self):
        brief = "Milo wears a green scarf."
        made = self.generate(image_mode="AI", visual_continuity=brief, review_script=True)
        made.refresh_from_db()
        self.assertEqual(made.settings["visual_continuity"], brief)
        self.assertIn(brief, self.get_reply.call_args.args[0])
        self.generate(image_mode="AI", visual_continuity=brief)
        made.refresh_from_db()
        self.assertEqual(made.settings["visual_continuity"], brief)
        self.create_image_scenes.assert_called_once()

    def test_ai_scene_editing_is_requested_and_saved_with_review_settings(self):
        generated = self.generate(ai_scene_editing=True, review_script=True)
        self.assertTrue(generated.settings["ai_scene_editing"])
        self.assertTrue(self.get_reply.call_args.kwargs["ai_scene_editing"])
        self.assertIn('"editing"', self.get_reply.call_args.args[0])

    def test_uses_the_voice_that_was_chosen(self):
        chosen = voice_model.make(name="nova")

        video = self.generate(avatar_selection="", voice_id=chosen.id)

        self.assertEqual(video.voice_model, chosen)

    def test_picks_a_voice_when_none_was_chosen(self):
        video = self.generate(avatar_selection="", voice_id="")

        self.assertIsNotNone(video.voice_model)

    def test_a_blank_avatar_does_not_send_generation_looking_for_one(self):
        video = self.generate(avatar_selection="", voice_id=self.voice.id)

        self.assertIsNone(video.avatar)
        self.assertEqual(video.voice_model, self.voice)

    def test_fills_the_video_in_and_leaves_it_ready(self):
        video = self.generate()

        self.assertEqual(video.status, "READY")
        self.assertEqual(video.title, "Cats and how they nap")
        self.assertEqual(video.gpt_answer, A_SCRIPT)
        self.assertEqual(video.dir_name, "media/videos/cats")

    def test_records_and_requests_the_selected_scene_count(self):
        generated = self.generate(scene_count=1)
        self.assertEqual(generated.settings["scene_count"], 1)
        self.assertIn("exactly 1 scenes", self.get_reply.call_args.args[0])

    def test_passes_scene_count_to_script_validation(self):
        generated = self.generate(scene_count=3)
        self.assertEqual(generated.gpt_answer, A_SCRIPT)
        self.assertEqual(generated.status, "READY")
        self.assertEqual(generated.settings["scene_count"], 3)
        self.assertEqual(self.get_reply.call_args.kwargs["scene_count"], 3)

    def test_records_the_choices_the_render_will_need(self):
        video = self.generate(
            subtitles=True, narration=False, avatar_position="left,top"
        )

        self.assertEqual(
            video.settings,
            dict(
                subtitles=True,
                narration=False,
                avatar_position="left,top",
                video_format="LANDSCAPE",
                platform="GENERAL",
                style="vivid",
                provider=None,
            ),
        )

    def test_web_mode_takes_precedence_over_a_stale_video_provider(self):
        self.generate(provider="sora", image_mode="WEB")
        prompt = self.get_reply.call_args.args[0]
        self.assertIn("concise image search query", prompt)
        self.assertNotIn("one achievable action", prompt)

    def test_asks_for_a_still_brief_for_an_image_provider(self):
        self.generate(provider="OPENAI", image_mode="AI")

        self.assertNotIn("camera move", self.get_reply.call_args.args[0])

    def test_asks_for_a_shot_brief_for_a_video_provider(self):
        # A still model wastes most of its value on "a tray of donuts", and the other
        # way round.
        self.generate(provider="sora", image_mode="AI")

        self.assertIn("camera move", self.get_reply.call_args.args[0])

    def test_new_builtin_video_providers_use_video_storyboards(self):
        for provider in ("kling", "runway", "gemini-video"):
            with self.subTest(provider=provider):
                self.generate(provider=provider, image_mode="AI")
                self.assertIn("camera move", self.get_reply.call_args.args[0])

    def test_custom_video_provider_uses_a_shot_brief(self):
        UserCustomVisualProvider.objects.create(
            user=self.user,
            name="Studio",
            output_type="VIDEO",
            endpoint_url="https://example.com/video",
            auth_type="none",
        )
        self.generate(provider="Studio", image_mode="AI")
        self.assertIn("camera move", self.get_reply.call_args.args[0])

    def test_another_users_video_provider_does_not_change_the_script(self):
        UserCustomVisualProvider.objects.create(
            user=user.make(),
            name="Studio",
            output_type="VIDEO",
            endpoint_url="https://example.com/video",
            auth_type="none",
        )
        self.generate(provider="Studio", image_mode="AI")
        self.assertNotIn("camera move", self.get_reply.call_args.args[0])

    def test_narrates_before_generating_the_visuals(self):
        # create_image_scene reads the narration length off disk to size a clip, so
        # the order matters.
        calls = []
        self.make_scenes_speech.side_effect = lambda *a, **k: calls.append("speech")
        self.create_image_scenes.side_effect = lambda *a, **k: calls.append("images")

        self.generate(provider="sora", image_mode="AI")

        self.assertEqual(calls, ["speech", "images"])

    def test_uses_the_avatars_own_voice_when_an_avatar_was_picked(self):
        picked = avatar.make(created_by=self.user)

        video = self.generate(avatar_selection=str(picked.id))

        self.assertEqual(video.avatar, picked)
        self.assertEqual(video.voice_model, picked.voice)

    def test_skips_the_visuals_entirely_when_no_image_mode_was_asked_for(self):
        self.generate(image_mode=False)

        self.create_image_scenes.assert_not_called()

    def test_carries_on_when_the_music_cannot_be_downloaded(self):
        self.download_music.side_effect = RuntimeError("video unavailable")

        self.assertEqual(self.generate().status, "READY")

    def test_rejects_foreign_assets_before_any_generation_work(self):
        for field, recipe in (
            ("avatar_selection", avatar),
            ("intro", intro),
            ("outro", outro),
        ):
            with self.subTest(field=field):
                foreign = recipe.make(created_by=user.make())
                with self.assertRaises(APIException) as error:
                    self.generate(**{field: str(foreign.id)})
                self.assertEqual(error.exception.status_code, 404)
                self.get_reply.assert_not_called()
                self.make_scenes_speech.assert_not_called()
                self.video.refresh_from_db()
                self.assertEqual(self.video.status, "GENERATION")

    def test_accepts_an_owned_intro_or_outro_independently(self):
        for field, recipe in (("intro", intro), ("outro", outro)):
            with self.subTest(field=field):
                asset = recipe.make(created_by=self.user)
                result = self.generate(**{field: str(asset.id)})
                self.assertEqual(getattr(result, field), asset)

    def test_rejects_a_foreign_private_voice_before_generating(self):
        foreign = voice_model.make(
            created_by=user.make(), type="CUSTOM_API", provider="private"
        )
        with self.assertRaises(APIException):
            self.generate(voice_id=str(foreign.id))
        self.get_reply.assert_not_called()


class ResumeGenerationTests(TestCase):
    def setUp(self):
        self.user = user.make()
        self.video = video.make(
            created_by=self.user,
            status="FAILED",
            mode="WEB",
            gpt_answer=A_SCRIPT,
            dir_name="media/videos/cats",
            settings=dict(narration=True, style="vivid", provider="bing"),
        )

        for name in ("make_scenes_speech", "create_image_scenes"):
            patcher = patch.object(VideoGenerationServices, name)
            setattr(self, name, patcher.start())
            self.addCleanup(patcher.stop)

    def test_carries_on_from_the_script_it_already_has(self):
        with patch.object(VideoGenerationServices, "get_reply") as asked:
            resumed = resume_video(self.video)

        asked.assert_not_called()
        self.assertEqual(resumed.gpt_answer, A_SCRIPT)
        self.assertEqual(resumed.status, "READY")

    def test_fills_in_the_narration_and_the_visuals_again(self):
        resume_video(self.video)

        self.make_scenes_speech.assert_called_once()
        self.create_image_scenes.assert_called_once()

    def test_asks_the_provider_the_first_run_chose(self):
        resume_video(self.video)

        self.assertEqual(self.create_image_scenes.call_args.kwargs["provider"], "bing")
        self.assertEqual(self.create_image_scenes.call_args.kwargs["style"], "vivid")

    def test_leaves_the_visuals_alone_for_a_video_that_asked_for_none(self):
        self.video.mode = None
        self.video.save()

        resume_video(self.video)

        self.create_image_scenes.assert_not_called()

    def test_refuses_a_video_that_never_got_a_script(self):
        self.video.gpt_answer = None
        self.video.save()

        with self.assertRaises(APIException):
            resume_video(self.video)
