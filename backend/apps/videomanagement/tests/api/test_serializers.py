import tempfile
from pathlib import Path

from django.conf import settings
from django.test import TestCase, override_settings
from rest_framework.test import APIRequestFactory

from apps.usermanagement.baker_recipes import user

from ...baker_recipes import avatar, music, scene, scene_image, video
from ...serializers import (
    AvatarSerializer,
    SceneSerializer,
    VideoNestedSerializer,
    VideoSerializer,
)
from ...request_serializers import (
    AddSceneSerializer,
    GenerateSerializer,
    VideoUpdateSerializer,
)


class SceneSerializerTests(TestCase):
    def test_carries_the_scenes_visual_alongside_it(self):
        line = scene.make()
        scene_image.make(scene=line)

        data = SceneSerializer(line).data

        self.assertEqual(data["scene_image"]["prompt"], "an image description")

    def test_reports_no_visual_rather_than_failing_when_there_is_none(self):
        line = scene.make()

        self.assertEqual(SceneSerializer(line).data["scene_image"], "")

    def test_reports_missing_narration_for_empty_and_stale_file_references(self):
        for filename in (None, "missing-narration.wav"):
            with self.subTest(filename=filename):
                line = scene.make(file=filename)
                self.assertEqual(SceneSerializer(line).data["narration_status"], "missing")

    def test_reports_available_narration_when_the_file_exists(self):
        with tempfile.TemporaryDirectory() as directory:
            with override_settings(MEDIA_ROOT=directory):
                Path(directory, "narration.wav").write_bytes(b"audio")
                line = scene.make(file="narration.wav")
                self.assertEqual(SceneSerializer(line).data["narration_status"], "available")

    def test_does_not_report_missing_narration_for_silent_videos(self):
        for options in ({"settings": {"narration": False}},):
            with self.subTest(options=options):
                line = scene.make(video=video.make(**options), file=None)
                self.assertEqual(SceneSerializer(line).data["narration_status"], "disabled")

    def test_video_detail_includes_each_scenes_narration_status(self):
        row = video.make()
        line = scene.make(video=row, file=None)
        data = VideoNestedSerializer(row).data
        self.assertEqual(data["scenes"][0]["id"], str(line.pk))
        self.assertEqual(data["scenes"][0]["narration_status"], "missing")


class VideoSerializerTests(TestCase):
    def test_names_the_music_rather_than_nesting_it(self):
        with_music = video.make(music=music.make())

        self.assertEqual(VideoSerializer(with_music).data["music"], "a song")

    def test_reports_no_music_rather_than_null(self):
        silent = video.make(music=None)

        self.assertEqual(VideoSerializer(silent).data["music"], "")

    def test_the_detail_view_carries_every_scene(self):
        with_scenes = video.make()
        scene.make(video=with_scenes, _quantity=3)

        self.assertEqual(len(VideoNestedSerializer(with_scenes).data["scenes"]), 3)


class AvatarSerializerTests(TestCase):
    def test_offers_the_voices_sample_so_a_client_can_play_it(self):
        natasha = avatar.make()

        self.assertEqual(AvatarSerializer(natasha).data["sample"], natasha.voice.sample)

    def test_survives_an_avatar_whose_voice_has_been_deleted(self):
        orphan = avatar.make()
        orphan.voice.delete()
        orphan.refresh_from_db()

        self.assertEqual(AvatarSerializer(orphan).data["sample"], "")


class SerializerWithRequest(TestCase):
    """created_by is a HiddenField fed by the request, so one has to be in context."""

    def setUp(self):
        self.user = user.make()
        request = APIRequestFactory().post("/")
        request.user = self.user
        self.context = {"request": request}


class GenerateSerializerTests(SerializerWithRequest):
    def valid(self, **overrides):
        data = {"message": "make me a video"}
        data.update(overrides)
        serializer = GenerateSerializer(data=data, context=self.context)
        serializer.is_valid()
        return serializer

    def test_needs_nothing_but_a_message(self):
        self.assertTrue(self.valid().is_valid())

    def test_rejects_a_request_with_no_message(self):
        self.assertFalse(GenerateSerializer(data={}, context=self.context).is_valid())

    def test_narrates_and_downloads_stills_from_the_web_by_default(self):
        data = self.valid().validated_data

        self.assertTrue(data["narration"])
        self.assertFalse(data["subtitles"])
        self.assertEqual(data["image_mode"], "WEB")

    def test_takes_narration_off_when_asked(self):
        self.assertFalse(self.valid(narration=False).validated_data["narration"])

    def test_rejects_a_model_the_pipeline_cannot_call(self):
        self.assertFalse(self.valid(gpt_model="not-a-model").is_valid())

    def test_advertises_the_configured_default_as_a_choice(self):
        # Otherwise a custom DEFAULT_GPT_MODEL would be offered and then rejected.

        self.assertIn(settings.DEFAULT_GPT_MODEL, settings.ACCEPTED_MODELS)

    def test_never_reads_the_owner_from_the_payload(self):
        # A client that posted created_by used to attribute the video, and its cost,
        # to another account.
        stranger = user.make()

        serializer = self.valid(created_by=stranger.id)

        self.assertEqual(serializer.validated_data["created_by"], self.user)


class AddSceneSerializerTests(TestCase):
    def test_an_ai_scene_needs_its_line(self):
        self.assertFalse(AddSceneSerializer(data={"mode": "AI"}).is_valid())
        self.assertTrue(
            AddSceneSerializer(data={"mode": "AI", "text": "a line"}).is_valid()
        )


    def test_a_scene_is_silent_and_not_the_last_unless_it_says_so(self):
        serializer = AddSceneSerializer(data={"mode": "AI", "text": "a line"})
        serializer.is_valid()

        self.assertFalse(serializer.validated_data["with_audio"])
        self.assertFalse(serializer.validated_data["is_last"])


class VideoUpdateSerializerTests(TestCase):
    def test_accepts_an_update_that_changes_only_the_title(self):
        serializer = VideoUpdateSerializer(data={"title": "A New Name"})

        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data, {"title": "A New Name"})

    def test_rejects_an_avatar_corner_that_does_not_exist(self):
        serializer = VideoUpdateSerializer(data={"avatar_position": "middle,middle"})

        self.assertFalse(serializer.is_valid())
