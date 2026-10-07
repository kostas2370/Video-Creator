"""Editing a video that already exists."""

from unittest.mock import patch

from django.test import TestCase
from apps.usermanagement.baker_recipes import user
from rest_framework.exceptions import APIException


from ...baker_recipes import (
    avatar,
    intro,
    outro,
    scene,
    video,
)
from ...services import (
    VideoServices,
)
from ...services.VideoServices import video_update
from ...models import Video


class VideoUpdateTests(TestCase):
    def setUp(self):
        self.video = video.make(created_by=user.make())

    def test_renames_the_video(self):
        updated = video_update(self.video, title="A New Name", avatar=None)

        self.assertEqual(updated.title, "A New Name")

    def test_a_stale_edit_preserves_a_workers_status(self):
        Video.objects.filter(pk=self.video.pk).update(status="RENDERING")
        video_update(self.video, title="New title")
        self.video.refresh_from_db()
        self.assertEqual(self.video.title, "New title")
        self.assertEqual(self.video.status, "RENDERING")

    def test_records_the_subtitle_and_avatar_choices(self):
        expected_settings = {
            **self.video.settings,
            "subtitles": True,
            "avatar_position": "left,top",
        }
        updated = video_update(
            self.video,
            title="t",
            avatar=None,
            subtitles=True,
            avatar_position="left,top",
        )

        self.assertEqual(updated.settings, expected_settings)

    def test_clears_the_avatar_when_none_was_chosen(self):
        self.video.avatar = avatar.make()

        for choice in (None, "", "None"):
            with self.subTest(choice=choice):
                self.assertIsNone(
                    video_update(self.video, title="t", avatar=choice).avatar
                )

    def test_re_records_every_line_when_the_avatar_brings_a_new_voice(self):
        picked = avatar.make(created_by=self.video.created_by)
        scene.make(video=self.video, _quantity=2)

        with patch.object(VideoServices, "update_scene") as resynthesise:
            updated = video_update(self.video, title="t", avatar=str(picked.id))

        self.assertEqual(updated.voice_model, picked.voice)
        self.assertEqual(resynthesise.call_count, 2)

    def test_leaves_the_recordings_alone_when_the_voice_is_unchanged(self):
        picked = avatar.make(voice=self.video.voice_model, created_by=self.video.created_by)

        with patch.object(VideoServices, "update_scene") as resynthesise:
            video_update(self.video, title="t", avatar=str(picked.id))

        resynthesise.assert_not_called()


    def test_attaches_the_intro_and_outro_that_were_chosen(self):
        opening = intro.make(created_by=self.video.created_by)
        closing = outro.make(created_by=self.video.created_by)

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

    def test_rejects_foreign_assets_before_mutating_or_regenerating(self):
        for field, recipe in (("avatar", avatar), ("intro", intro), ("outro", outro)):
            with self.subTest(field=field):
                foreign = recipe.make(created_by=user.make())
                owned_avatar = avatar.make(created_by=self.video.created_by)
                original_title = self.video.title
                original_voice = self.video.voice_model_id
                params = {"avatar": str(owned_avatar.id), field: str(foreign.id)}
                with patch.object(VideoServices, "update_scene") as regenerate:
                    with self.assertRaises(APIException) as error:
                        video_update(self.video, title="Changed", **params)
                self.assertEqual(error.exception.status_code, 404)
                regenerate.assert_not_called()
                self.assertEqual(self.video.title, original_title)
                self.video.refresh_from_db()
                self.assertEqual(self.video.title, original_title)
                self.assertEqual(self.video.voice_model_id, original_voice)
