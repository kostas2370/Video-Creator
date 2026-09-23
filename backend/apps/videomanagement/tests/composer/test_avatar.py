"""Compositing the talking head onto a finished render."""

from unittest.mock import patch

from django.test import TestCase

from ...baker_recipes import avatar, video
from ...utils.composer import avatar as avatar_utils
from ...utils.composer.avatar import handle_avatar_video
from ..doubles import FakeClip


class HandleAvatarVideoTests(TestCase):
    def setUp(self):
        self.video = video.make(avatar=avatar.make(), settings={})
        self.final = FakeClip()

    def test_renders_without_the_avatar_when_it_could_not_be_made(self):
        with (
            patch.object(avatar_utils.os.path, "exists", return_value=False),
            patch.object(avatar_utils, "create_avatar_video", return_value=""),
            patch.object(avatar_utils, "VideoFileClip") as video_file_clip,
        ):
            self.assertIs(handle_avatar_video(self.video, self.final), self.final)

        video_file_clip.assert_not_called()

    def test_composites_the_avatar_it_already_has_on_disk(self):
        composited = FakeClip()

        with (
            patch.object(avatar_utils.os.path, "exists", return_value=True),
            patch.object(avatar_utils, "create_avatar_video") as made,
            patch.object(avatar_utils, "VideoFileClip", return_value=FakeClip()),
            patch.object(
                avatar_utils, "CompositeVideoClip", return_value=composited
            ) as layered,
        ):
            self.assertIs(handle_avatar_video(self.video, self.final), composited)

        made.assert_not_called()
        layered.assert_called_once()

    def test_reads_the_corner_the_video_asked_for(self):
        self.video.settings = dict(avatar_position="left,bottom")
        clip = FakeClip()

        with (
            patch.object(avatar_utils.os.path, "exists", return_value=True),
            patch.object(avatar_utils, "VideoFileClip", return_value=clip),
            patch.object(avatar_utils, "CompositeVideoClip", return_value=FakeClip()),
        ):
            handle_avatar_video(self.video, self.final)

        self.assertIn("set_position", clip.effects)

    def test_survives_a_video_with_no_settings(self):
        self.video.settings = None
        composited = FakeClip()

        with (
            patch.object(avatar_utils.os.path, "exists", return_value=True),
            patch.object(avatar_utils, "VideoFileClip", return_value=FakeClip()),
            patch.object(avatar_utils, "CompositeVideoClip", return_value=composited),
        ):
            self.assertIs(handle_avatar_video(self.video, self.final), composited)
