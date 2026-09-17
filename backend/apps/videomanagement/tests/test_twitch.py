"""The Twitch client, with requests and urlretrieve stubbed — no call leaves the box."""

from unittest.mock import MagicMock, patch

import requests
from django.test import SimpleTestCase, override_settings
from rest_framework.exceptions import APIException

from ..utils import twitch
from ..utils.exceptions import (
    GameNotFound,
    HeaderInitiationException,
    InvalidTwitchToken,
    StreamerNotFound,
)
from ..utils.twitch import TwitchClient


def a_response(payload=None, status_code=200):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = payload if payload is not None else {}
    if status_code >= 400:
        error = requests.exceptions.HTTPError(response=response)
        response.raise_for_status.side_effect = error

    return response


class SetHeadersTests(SimpleTestCase):
    @override_settings(TWITCH_CLIENT="a-client", TWITCH_CLIENT_SECRET="a-secret")
    def test_exchanges_the_credentials_for_a_bearer_token(self):
        client = TwitchClient("media/videos/v")

        with patch.object(
            twitch.requests, "post", return_value=a_response({"access_token": "tok"})
        ):
            headers = client.set_headers()

        self.assertEqual(headers["Authorization"], "Bearer tok")
        self.assertEqual(headers["Client-Id"], "a-client")
        self.assertEqual(client.headers, headers)

    @override_settings(TWITCH_CLIENT="a-client", TWITCH_CLIENT_SECRET="a-secret")
    def test_raises_when_twitch_will_not_issue_a_token(self):
        with patch.object(
            twitch.requests, "post", return_value=a_response(status_code=401)
        ):
            with self.assertRaises(APIException):
                TwitchClient("media/videos/v").set_headers()


class ClientWithHeaders(SimpleTestCase):
    def setUp(self):
        self.client = TwitchClient("media/videos/v")
        self.client.headers = {"Authorization": "Bearer tok", "Client-Id": "a-client"}


class GetGameIdTests(ClientWithHeaders):
    def test_returns_the_id_twitch_reports(self):
        with patch.object(
            twitch.requests, "get", return_value=a_response({"data": [{"id": "33214"}]})
        ):
            self.assertEqual(self.client.get_game_id("Fortnite"), "33214")

    def test_refuses_to_call_before_the_token_is_fetched(self):
        with self.assertRaises(HeaderInitiationException):
            TwitchClient("media/videos/v").get_game_id("Fortnite")

    def test_reports_an_unknown_game(self):
        with patch.object(
            twitch.requests, "get", return_value=a_response(status_code=400)
        ):
            with self.assertRaises(GameNotFound):
                self.client.get_game_id("Not A Game")

    def test_reports_an_expired_token(self):
        with patch.object(
            twitch.requests, "get", return_value=a_response(status_code=401)
        ):
            with self.assertRaises(InvalidTwitchToken):
                self.client.get_game_id("Fortnite")


class GetStreamerIdTests(ClientWithHeaders):
    def test_returns_the_id_twitch_reports(self):
        with patch.object(
            twitch.requests, "get", return_value=a_response({"data": [{"id": "1234"}]})
        ):
            self.assertEqual(self.client.get_streamer_id("someone"), "1234")

    def test_reports_an_unknown_streamer(self):
        with patch.object(
            twitch.requests,
            "get",
            return_value=a_response({"data": []}, status_code=400),
        ):
            with self.assertRaises(StreamerNotFound):
                self.client.get_streamer_id("nobody")


class GetClipsTests(ClientWithHeaders):
    def test_asks_for_a_games_clips_by_game_id(self):
        with patch.object(
            twitch.requests, "get", return_value=a_response({"data": [{"id": "c1"}]})
        ) as get:
            clips = self.client.get_clips("33214", mode="game")

        self.assertEqual(clips, [{"id": "c1"}])
        self.assertIn("game_id=33214", get.call_args.args[0])

    def test_asks_for_a_streamers_clips_by_broadcaster_id(self):
        with patch.object(
            twitch.requests, "get", return_value=a_response({"data": []})
        ) as get:
            self.client.get_clips("1234", mode="streamer")

        self.assertIn("broadcaster_id=1234", get.call_args.args[0])

    def test_narrows_the_window_when_a_start_date_is_given(self):
        with patch.object(
            twitch.requests, "get", return_value=a_response({"data": []})
        ) as get:
            self.client.get_clips("33214", start_date="2026-01-01")

        self.assertIn("started_at=2026-01-01T00:00:00Z", get.call_args.args[0])

    def test_returns_nothing_when_the_request_fails(self):
        with patch.object(
            twitch.requests, "get", return_value=a_response(status_code=500)
        ):
            self.assertIsNone(self.client.get_clips("33214"))


class GetClipByUrlTests(ClientWithHeaders):
    def test_looks_the_clip_up_by_the_id_in_the_url(self):
        with patch.object(
            twitch.requests, "get", return_value=a_response({"data": [{"id": "abc"}]})
        ) as get:
            clips = self.client.get_clip_by_url("https://clips.twitch.tv/abc?t=1")

        self.assertEqual(clips, [{"id": "abc"}])
        self.assertIn("id=abc", get.call_args.args[0])

    def test_reports_a_url_that_matches_no_clip(self):
        with patch.object(
            twitch.requests, "get", return_value=a_response({"data": []})
        ):
            with self.assertRaises(APIException):
                self.client.get_clip_by_url("https://clips.twitch.tv/nothing")

    def test_reports_a_url_twitch_rejects(self):
        with patch.object(
            twitch.requests, "get", return_value=a_response(status_code=404)
        ):
            with self.assertRaises(APIException):
                self.client.get_clip_by_url("https://clips.twitch.tv/abc")


class DownloadClipTests(ClientWithHeaders):
    def test_turns_the_thumbnail_url_into_the_mp4_and_saves_it(self):
        clip = {"thumbnail_url": "https://cdn.test/abc-preview-480x272.jpg"}

        with patch.object(twitch.urllib.request, "urlretrieve") as retrieve:
            path = self.client.download_clip(clip)

        self.assertTrue(path.startswith("media/videos/v/"))
        self.assertTrue(path.endswith(".mp4"))
        self.assertEqual(retrieve.call_args.args[0], "https://cdn.test/abc.mp4")

    def test_returns_nothing_when_the_download_fails(self):
        # One unavailable clip must not take the whole video down with it.
        clip = {"thumbnail_url": "https://cdn.test/abc-preview-480x272.jpg"}

        with patch.object(
            twitch.urllib.request, "urlretrieve", side_effect=OSError("404")
        ):
            self.assertIsNone(self.client.download_clip(clip))

    def test_returns_nothing_for_a_clip_with_no_thumbnail(self):
        self.assertIsNone(self.client.download_clip({}))
