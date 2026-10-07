"""The worker jobs. Each one owns a video and must leave it in a terminal status."""

from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.apikeysmanagement.models import Provider
from apps.usermanagement.baker_recipes import user
from apps.apikeysmanagement.baker_recipes import user_custom_tts_provider
from ..baker_recipes import video
from ..models import Video, VoiceModel, VoiceModelType
from ..utils import tts_utils
from ..tasks import (
    update_user_voices,
    resume_video_task,
    generate_video_task,
    reap_stalled_videos,
    render_video_task,
)


class TaskFailureTests(TestCase):
    def setUp(self):
        self.video = video.make(status="GENERATION")

    def test_generation_leaves_the_video_failed_and_re_raises(self):
        with patch(
            "apps.videomanagement.services.VideoGenerationServices.generate_video",
            side_effect=RuntimeError("the model refused"),
        ):
            with self.assertRaises(RuntimeError):
                generate_video_task(video_id=self.video.id)

        self.video.refresh_from_db()
        self.assertEqual(self.video.status, "FAILED")


    def test_rendering_leaves_the_video_failed_and_re_raises(self):
        with patch(
            "apps.videomanagement.utils.composer.render.make_video",
            side_effect=RuntimeError("the encoder died"),
        ):
            with self.assertRaises(RuntimeError):
                render_video_task(video_id=self.video.id)

        self.video.refresh_from_db()
        self.assertEqual(self.video.status, "FAILED")

    def test_resuming_leaves_the_video_failed_and_re_raises(self):
        with patch(
            "apps.videomanagement.services.VideoGenerationServices.resume_video",
            side_effect=RuntimeError("the provider is still down"),
        ):
            with self.assertRaises(RuntimeError):
                resume_video_task(video_id=self.video.id)

        self.video.refresh_from_db()
        self.assertEqual(self.video.status, "FAILED")


class TaskSuccessTests(TestCase):
    def setUp(self):
        self.video = video.make(status="GENERATION")

    def test_generation_hands_its_parameters_to_the_service(self):
        with patch(
            "apps.videomanagement.services.VideoGenerationServices.generate_video"
        ) as generate:
            returned = generate_video_task(video_id=self.video.id, message="cats")

        self.assertEqual(returned, self.video.id)
        self.assertEqual(generate.call_args.kwargs["message"], "cats")
        self.assertEqual(generate.call_args.kwargs["video"].pk, self.video.pk)

    def test_rendering_hands_the_video_to_make_video(self):
        with patch("apps.videomanagement.utils.composer.render.make_video") as render:
            self.assertEqual(render_video_task(video_id=self.video.id), self.video.id)

        self.assertEqual(render.call_args.args[0].pk, self.video.pk)

    def test_resuming_hands_the_video_to_the_service(self):
        with patch(
            "apps.videomanagement.services.VideoGenerationServices.resume_video"
        ) as resume:
            returned = resume_video_task(video_id=self.video.id)

        self.assertEqual(returned, self.video.id)
        self.assertEqual(resume.call_args.args[0].pk, self.video.pk)


class UpdateUserVoicesTests(TestCase):
    def setUp(self):
        self.user = user.make()

    def labs_returns(self, *voices):
        return patch(
            "apps.videomanagement.utils.tts_utils.get_voices_from_elevenlabs",
            return_value=list(voices),
        )

    def custom_provider_returns(self, voices):
        return patch(
            "apps.videomanagement.utils.tts_utils.get_voices_from_custom_provider",
            return_value=voices,
        )

    def test_imports_the_voices_against_the_user_who_owns_the_key(self):
        with self.labs_returns(
            {"name": "Rachel", "voice_id": "abc", "preview_url": "https://a.test/x"}
        ):
            added = update_user_voices(self.user.id, Provider.ELEVENLABS)

        voice = VoiceModel.objects.get(path="abc")
        self.assertEqual(added, 1)
        self.assertEqual(voice.created_by, self.user)
        self.assertEqual(voice.provider, "ELEVENLABS")
        self.assertEqual(voice.type, "API")

    def test_running_it_twice_does_not_duplicate_anything(self):
        voices = [{"name": "Rachel", "voice_id": "abc", "preview_url": ""}]

        with self.labs_returns(*voices):
            update_user_voices(self.user.id, Provider.ELEVENLABS)
            added = update_user_voices(self.user.id, Provider.ELEVENLABS)

        self.assertEqual(added, 0)
        self.assertEqual(VoiceModel.objects.filter(path="abc").count(), 1)

    def test_two_users_can_hold_a_voice_of_the_same_name(self):
        stranger = user.make()
        voices = [{"name": "Rachel", "voice_id": "abc", "preview_url": ""}]

        with self.labs_returns(*voices):
            update_user_voices(self.user.id, Provider.ELEVENLABS)
            update_user_voices(stranger.id, Provider.ELEVENLABS)

        self.assertEqual(VoiceModel.objects.filter(name="Rachel").count(), 2)

    def test_does_nothing_for_a_user_who_no_longer_exists(self):
        self.assertEqual(update_user_voices(999999, Provider.ELEVENLABS), 0)

    def test_a_provider_that_will_not_answer_fails_the_import(self):
        owner = user.make()

        with patch.object(
            tts_utils, "get_voices_from_elevenlabs", side_effect=RuntimeError("401")
        ):
            with self.assertRaises(RuntimeError):
                update_user_voices(owner.id, Provider.ELEVENLABS)

        self.assertEqual(VoiceModel.objects.count(), 0)

    def test_updates_the_voices_from_a_custom_provider(self):
        custom_provider = user_custom_tts_provider.make(user=self.user)

        with self.custom_provider_returns(
            [{"name": "Rachel", "id": "abc", "preview_url": "https://a.test/x"}]
        ):
            added = update_user_voices(self.user.id, custom_provider.name)

        voice = VoiceModel.objects.get(path="abc")
        self.assertEqual(added, 1)
        self.assertEqual(voice.created_by, self.user)
        self.assertEqual(voice.provider, custom_provider.name)
        self.assertEqual(voice.type, VoiceModelType.CUSTOM_API)

    def test_imported_builtin_voices_are_visible_and_route_to_the_matching_tts(self):
        self.user.use_service_api_keys = False
        self.user.save(update_fields=["use_service_api_keys"])
        for provider, fetcher, handler in (
            (Provider.ELEVENLABS, "get_voices_from_elevenlabs", "tts_from_elevenlabs"),
            (Provider.SIXTYDB, "get_voices_from_sixtydb", "tts_from_sixtydb"),
        ):
            with self.subTest(provider=provider):
                with patch.object(tts_utils, fetcher, autospec=True) as fetch:
                    fetch.return_value = [{"name": "A voice", "voice_id": "abc"}]
                    update_user_voices(self.user.id, provider)
                fetch.assert_called_once_with(user=self.user)

                voice = VoiceModel.objects.get(provider=provider, path="abc")
                with patch(
                    "apps.videomanagement.models.ApiKeys.key_for", return_value="key"
                ):
                    self.assertIn(voice, VoiceModel.available_to(self.user))
                with patch.object(tts_utils, handler) as synthesize:
                    tts_utils.save(
                        tts_utils.ApiSyn(provider=voice.provider, path=voice.path),
                        "hello",
                        "out.wav",
                        user=self.user,
                    )
                synthesize.assert_called_once_with(
                    "hello", "out.wav", "abc", user=self.user, provider_name=provider
                )

    def imported_custom_voice(self, path="abc"):
        return VoiceModel.objects.create(
            created_by=self.user,
            name="Original voice",
            provider="Studio",
            type=VoiceModelType.CUSTOM_API,
            path=path,
            sample="https://example.com/old.mp3",
        )

    def test_a_failed_custom_fetch_preserves_imported_voices(self):
        existing = self.imported_custom_voice()
        with self.custom_provider_returns(None):
            self.assertEqual(update_user_voices(self.user.pk, "Studio"), 0)
        self.assertTrue(VoiceModel.objects.filter(pk=existing.pk).exists())

    def test_an_empty_successful_fetch_removes_only_that_users_provider_voices(self):
        existing = self.imported_custom_voice()
        other = VoiceModel.objects.create(
            created_by=user.make(),
            name="Another voice",
            provider="Studio",
            type=VoiceModelType.CUSTOM_API,
            path="abc",
        )
        with self.custom_provider_returns([]):
            update_user_voices(self.user.pk, "Studio")
        self.assertFalse(VoiceModel.objects.filter(pk=existing.pk).exists())
        self.assertTrue(VoiceModel.objects.filter(pk=other.pk).exists())

    def test_refresh_updates_the_name_and_preview_without_replacing_the_voice(self):
        existing = self.imported_custom_voice()
        with self.custom_provider_returns(
            [
                {
                    "id": "abc",
                    "name": "Renamed voice",
                    "preview_url": "https://example.com/new.mp3",
                }
            ]
        ):
            self.assertEqual(update_user_voices(self.user.pk, "Studio"), 0)
        existing.refresh_from_db()
        self.assertEqual(existing.name, "Renamed voice")
        self.assertEqual(existing.sample, "https://example.com/new.mp3")

    def test_numeric_custom_ids_do_not_recreate_existing_voices(self):
        existing = self.imported_custom_voice(path="123")
        with self.custom_provider_returns([{"id": 123, "name": "Original voice"}]):
            self.assertEqual(update_user_voices(self.user.pk, "Studio"), 0)
        self.assertTrue(VoiceModel.objects.filter(pk=existing.pk).exists())

    def test_malformed_custom_results_do_not_delete_previously_imported_voices(self):
        existing = self.imported_custom_voice()
        with self.custom_provider_returns([{"id": "new-without-a-name"}]):
            with self.assertRaises(KeyError):
                update_user_voices(self.user.pk, "Studio")
        self.assertTrue(VoiceModel.objects.filter(pk=existing.pk).exists())


class ReapStalledVideosTests(TestCase):
    """A task killed without unwinding never reaches its own except clause."""

    def stale(self, status, age_seconds):
        stalled = video.make(status=status)
        # updated_at is auto_now, so it has to be written past the ORM.
        Video.objects.filter(pk=stalled.pk).update(
            updated_at=timezone.now() - timedelta(seconds=age_seconds)
        )
        return stalled

    @override_settings(VIDEO_TASK_STALE_AFTER=3600)
    def test_fails_a_video_no_worker_can_still_be_holding(self):
        video = self.stale("RENDERING", 7200)

        self.assertEqual(reap_stalled_videos(), 1)
        video.refresh_from_db()
        self.assertEqual(video.status, "FAILED")

    @override_settings(VIDEO_TASK_STALE_AFTER=3600)
    def test_leaves_a_video_a_worker_is_still_on(self):
        video = self.stale("GENERATION", 60)

        self.assertEqual(reap_stalled_videos(), 0)
        video.refresh_from_db()
        self.assertEqual(video.status, "GENERATION")

    @override_settings(VIDEO_TASK_STALE_AFTER=3600)
    def test_leaves_videos_that_already_reached_an_answer(self):
        for status in ("READY", "COMPLETED", "FAILED"):
            with self.subTest(status=status):
                video = self.stale(status, 7200)

                reap_stalled_videos()

                video.refresh_from_db()
                self.assertEqual(video.status, status)


class CreateSceneTaskTests(TestCase):
    def setUp(self):
        self.video = video.make(status="GENERATION")
        self.data = {"text": "New scene"}

    def test_creates_every_reviewed_sentence_in_order_before_marking_ready(self):
        from ..tasks import create_scene_task

        scenes = [{"text": "First."}, {"text": "Second.", "is_last": True}]
        observed_statuses = []
        def capture(*args):
            self.video.refresh_from_db()
            observed_statuses.append(self.video.status)
        with patch("apps.videomanagement.services.SceneServices.create_scene", side_effect=capture) as create:
            create_scene_task(self.video.pk, {"scenes": scenes})
        self.assertEqual([call.args[1] for call in create.call_args_list], scenes)
        self.assertEqual(observed_statuses, ["GENERATION", "GENERATION"])
        self.video.refresh_from_db()
        self.assertEqual(self.video.status, "READY")

    def test_creates_scene_and_marks_video_ready(self):
        from ..tasks import create_scene_task
        with patch("apps.videomanagement.services.SceneServices.create_scene") as create:
            create_scene_task(self.video.pk, self.data)
            create_scene_task(self.video.pk, self.data)
        create.assert_called_once_with(self.video, self.data, {})
        self.video.refresh_from_db()
        self.assertEqual(self.video.status, "READY")

    def test_failure_marks_video_failed(self):
        from ..tasks import create_scene_task
        with patch("apps.videomanagement.services.SceneServices.create_scene", side_effect=RuntimeError("provider error")):
            with self.assertRaises(RuntimeError):
                create_scene_task(self.video.pk, self.data)
        self.video.refresh_from_db()
        self.assertEqual(self.video.status, "FAILED")

    def test_upload_survives_request_and_is_copied_before_cleanup(self):
        import tempfile
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.core.files.storage import default_storage
        from ..baker_recipes import scene
        from ..models import SceneImage
        from ..tasks import create_scene_task
        with tempfile.TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            path = default_storage.save("media/scene_uploads/visual.png", SimpleUploadedFile("visual.png", b"image bytes"))
            line = scene.make(video=self.video)
            with patch("apps.videomanagement.services.SceneServices.make_scene_speech", return_value=line):
                create_scene_task(self.video.pk, self.data, path)
            image = SceneImage.objects.get(scene=line)
            self.assertNotEqual(image.file.name, path)
            with image.file.open("rb") as saved:
                self.assertEqual(saved.read(), b"image bytes")
            self.assertFalse(default_storage.exists(path))

    def test_failure_cleans_up_staged_upload(self):
        from ..tasks import create_scene_task
        with (
            patch("apps.videomanagement.tasks.default_storage.open", side_effect=OSError("unavailable")),
            patch("apps.videomanagement.tasks.default_storage.delete") as cleanup,
        ):
            with self.assertRaises(OSError):
                create_scene_task(self.video.pk, self.data, "media/scene_uploads/file.png")
        cleanup.assert_called_once_with("media/scene_uploads/file.png")
