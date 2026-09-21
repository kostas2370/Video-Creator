from django.test import TestCase
from rest_framework.test import APIRequestFactory

from apps.usermanagement.baker_recipes import user

from ..baker_recipes import avatar, music, scene, scene_image, video
from ..serializers import (
    AvatarSerializer,
    SceneSerializer,
    VideoNestedSerializer,
    VideoSerializer,
)
from ..swagger_serializers import (
    AddSceneSerializer,
    GenerateSerializer,
    TwitchSerializer,
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


class VideoSerializerTests(TestCase):
    def test_names_the_music_rather_than_nesting_it(self):
        with_music = video.make(music=music.make())

        self.assertEqual(VideoSerializer(with_music).data["music"], "a song")

    def test_reports_no_music_rather_than_null(self):
        silent = video.make(music=None)

        self.assertEqual(VideoSerializer(silent).data["music"], "")

    def test_the_detail_view_carries_every_scene(self):
        with_scenes = video.make()
        scene.make(prompt=with_scenes.prompt, _quantity=3)

        self.assertEqual(len(VideoNestedSerializer(with_scenes).data["scenes"]), 3)


class AvatarSerializerTests(TestCase):
    def test_offers_the_voices_sample_so_a_client_can_play_it(self):
        natasha = avatar.make()

        self.assertEqual(AvatarSerializer(natasha).data["sample"], natasha.voice.sample)


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
        from django.conf import settings

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

    def test_a_twitch_scene_needs_its_clip(self):
        self.assertFalse(AddSceneSerializer(data={"mode": "TWITCH"}).is_valid())
        self.assertTrue(
            AddSceneSerializer(
                data={"mode": "TWITCH", "url": "https://clips.twitch.tv/abc"}
            ).is_valid()
        )

    def test_a_scene_is_silent_and_not_the_last_unless_it_says_so(self):
        serializer = AddSceneSerializer(data={"mode": "AI", "text": "a line"})
        serializer.is_valid()

        self.assertFalse(serializer.validated_data["with_audio"])
        self.assertFalse(serializer.validated_data["is_last"])


class TwitchSerializerTests(SerializerWithRequest):
    def valid(self, **overrides):
        data = {"mode": "game", "value": "Fortnite", "amt": 5}
        data.update(overrides)
        return TwitchSerializer(data=data, context=self.context)

    def test_accepts_a_game_or_a_streamer(self):
        self.assertTrue(self.valid(mode="game").is_valid())
        self.assertTrue(self.valid(mode="streamer").is_valid())
        self.assertFalse(self.valid(mode="playlist").is_valid())

    def test_will_not_collect_more_clips_than_the_cap(self):
        self.assertFalse(self.valid(amt=50).is_valid())

    def test_leaves_the_window_open_when_no_start_date_is_given(self):
        serializer = self.valid()
        serializer.is_valid()

        self.assertIsNone(serializer.validated_data["started_at"])


class VideoUpdateSerializerTests(TestCase):
    def test_accepts_an_update_that_changes_only_the_title(self):
        serializer = VideoUpdateSerializer(data={"title": "A New Name"})

        self.assertTrue(serializer.is_valid())
        self.assertIsNone(serializer.validated_data["intro"])

    def test_rejects_an_avatar_corner_that_does_not_exist(self):
        serializer = VideoUpdateSerializer(data={"avatar_position": "middle,middle"})

        self.assertFalse(serializer.is_valid())
