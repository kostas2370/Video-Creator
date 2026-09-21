"""Twitch clip generation, with the Twitch API stubbed."""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.usermanagement.baker_recipes import user

from ...services import (
    TwitchGenerationService,
)
from ...services.TwitchGenerationService import (
    generate_twitch_video,
    twitch_video_title,
)
from ...services.VideoGenerationServices import create_pending_video


class TwitchGenerationTests(TestCase):
    def setUp(self):
        self.user = user.make()
        self.video = create_pending_video(
            "clips", created_by=self.user, video_type="TWITCH", title="Fortnite"
        )
        self.client = MagicMock()
        self.client.get_game_id.return_value = "33214"
        self.client.get_streamer_id.return_value = "1234"
        self.client.get_clips.return_value = [
            {"title": f"clip {n}", "url": f"https://clips.twitch.tv/{n}"}
            for n in range(3)
        ]
        self.client.download_clip.side_effect = (
            lambda clip: f"clips/{clip['title']}.mp4"
        )

        for name, value in (
            ("TwitchClient", self.client),
            ("generate_directory", "media/videos/fortnite"),
            ("create_twitch_clip_scene", None),
            ("charge_user", 0.05),
        ):
            patcher = patch.object(TwitchGenerationService, name, return_value=value)
            setattr(self, name, patcher.start())
            self.addCleanup(patcher.stop)

    def test_titles_the_video_with_the_day_it_was_made(self):
        self.assertTrue(twitch_video_title("Fortnite").startswith("Fortnite "))

    def test_collects_the_clips_and_leaves_the_video_ready(self):
        video = generate_twitch_video(self.video, mode="game", value="Fortnite")

        self.assertEqual(video.status, "READY")
        self.assertEqual(self.create_twitch_clip_scene.call_count, 3)

    def test_looks_a_game_up_by_name(self):
        generate_twitch_video(self.video, mode="game", value="Fortnite")

        self.client.get_game_id.assert_called_once_with("Fortnite")
        self.client.get_streamer_id.assert_not_called()

    def test_looks_a_streamer_up_by_name(self):
        generate_twitch_video(self.video, mode="streamer", value="someone")

        self.client.get_streamer_id.assert_called_once_with("someone")

    def test_takes_no_more_clips_than_were_asked_for(self):
        generate_twitch_video(self.video, mode="game", value="Fortnite", amt=2)

        self.assertEqual(self.create_twitch_clip_scene.call_count, 2)

    def test_credits_every_clip_it_used(self):
        video = generate_twitch_video(self.video, mode="game", value="Fortnite")

        self.assertIn("https://clips.twitch.tv/0", video.gpt_answer)
        self.assertIn("clip 2", video.gpt_answer)

    def test_skips_a_clip_that_would_not_download(self):
        self.client.download_clip.side_effect = [None, "clips/b.mp4", None]

        video = generate_twitch_video(self.video, mode="game", value="Fortnite")

        self.assertEqual(self.create_twitch_clip_scene.call_count, 1)
        self.assertEqual(video.status, "READY")

    def test_charges_the_owner_against_their_twitch_balance(self):
        video = generate_twitch_video(self.video, mode="game", value="Fortnite")

        self.charge_user.assert_called_once_with(
            self.user, "generation_limit_for_twitch", video
        )
