"""Editing a video that already exists."""

from unittest.mock import patch

from django.test import TestCase
from rest_framework.exceptions import APIException


from ...baker_recipes import (
    avatar,
    intro,
    outro,
    scene,
    twitch_video,
    video,
)
from ...services import (
    VideoServices,
)
from ...services.VideoServices import video_update


class VideoUpdateTests(TestCase):
    def setUp(self):
        self.video = video.make()

    def test_renames_the_video(self):
        updated = video_update(self.video, title="A New Name", avatar=None)

        self.assertEqual(updated.title, "A New Name")

    def test_records_the_subtitle_and_avatar_choices(self):
        updated = video_update(
            self.video,
            title="t",
            avatar=None,
            subtitles=True,
            avatar_position="left,top",
        )

        self.assertEqual(
            updated.settings, dict(subtitles=True, avatar_position="left,top")
        )

    def test_clears_the_avatar_when_none_was_chosen(self):
        self.video.avatar = avatar.make()

        for choice in (None, "", "None"):
            with self.subTest(choice=choice):
                self.assertIsNone(
                    video_update(self.video, title="t", avatar=choice).avatar
                )

    def test_re_records_every_line_when_the_avatar_brings_a_new_voice(self):
        picked = avatar.make()
        scene.make(video=self.video, _quantity=2)

        with patch.object(VideoServices, "update_scene") as resynthesise:
            updated = video_update(self.video, title="t", avatar=str(picked.id))

        self.assertEqual(updated.voice_model, picked.voice)
        self.assertEqual(resynthesise.call_count, 2)

    def test_leaves_the_recordings_alone_when_the_voice_is_unchanged(self):
        picked = avatar.make(voice=self.video.voice_model)

        with patch.object(VideoServices, "update_scene") as resynthesise:
            video_update(self.video, title="t", avatar=str(picked.id))

        resynthesise.assert_not_called()

    def test_never_gives_a_twitch_video_an_avatar(self):
        clips = twitch_video.make()
        picked = avatar.make()

        self.assertIsNone(video_update(clips, title="t", avatar=str(picked.id)).avatar)

    def test_attaches_the_intro_and_outro_that_were_chosen(self):
        opening = intro.make()
        closing = outro.make()

        updated = video_update(
            self.video,
            title="t",
            avatar=None,
            intro=str(opening.id),
            outro=str(closing.id),
        )

        self.assertEqual(updated.intro, opening)
        self.assertEqual(updated.outro, closing)

    def test_reports_an_intro_that_does_not_exist(self):
        with self.assertRaises(APIException):
            video_update(self.video, title="t", avatar=None, intro="99999")

    def test_reports_an_outro_that_does_not_exist(self):
        with self.assertRaises(APIException):
            video_update(self.video, title="t", avatar=None, outro="99999")
