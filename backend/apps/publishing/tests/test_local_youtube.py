from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from apps.publishing.config import callback_url, local_youtube_origin, setup_message
from apps.publishing.connections import youtube
from apps.publishing.models import Platform
from .test_connections import CONFIG


@override_settings(DEBUG=True, ENV="dev", SOCIAL_PUBLISHING=CONFIG,
                   FRONTEND_URL="http://localhost:3000", SOCIAL_PUBLIC_BASE_URL="http://localhost:3000")
class LocalYouTubeConfigTests(SimpleTestCase):
    def test_local_youtube_authorization_and_token_exchange_use_exact_callback(self):
        self.assertEqual(setup_message(Platform.YOUTUBE), "")
        expected = "http://localhost:3000/api/publishing/oauth/youtube/callback/"
        self.assertEqual(callback_url(Platform.YOUTUBE), expected)
        params = parse_qs(urlparse(youtube.authorization_url("state")).query)
        self.assertEqual(params["redirect_uri"], [expected])
        with patch.object(youtube, "request_json", return_value={"access_token": "test"}) as request:
            youtube.exchange_code("code")
        self.assertEqual(request.call_args.kwargs["data"]["redirect_uri"], expected)

    def test_other_platforms_and_production_still_require_https(self):
        for platform in (Platform.TIKTOK, Platform.INSTAGRAM):
            self.assertTrue(setup_message(platform))
        for changes in ({"DEBUG": False}, {"ENV": "prod"}):
            with self.subTest(**changes), override_settings(**changes):
                self.assertTrue(setup_message(Platform.YOUTUBE))
                self.assertFalse(local_youtube_origin(Platform.YOUTUBE))

    def test_http_hosts_and_malformed_origins_are_rejected(self):
        for origin in (
            "http://127.0.0.1:3000", "http://192.168.1.10:3000", "http://localhost.evil.test:3000",
            "http://localhost@evil.test", "http://user@localhost:3000", "http://localhost:99999",
            "http://localhost:bad", "http://localhost:3000/path", "http://localhost:3000?x=1",
            "http://localhost:3000#fragment", "http://[invalid", "http://example.test",
        ):
            with self.subTest(origin=origin), override_settings(SOCIAL_PUBLIC_BASE_URL=origin, FRONTEND_URL=origin):
                self.assertTrue(setup_message(Platform.YOUTUBE))
                self.assertFalse(local_youtube_origin(Platform.YOUTUBE))

    def test_mixed_frontend_and_callback_origins_are_rejected(self):
        with override_settings(FRONTEND_URL="http://127.0.0.1:3000"):
            self.assertTrue(setup_message(Platform.YOUTUBE))

    def test_https_remains_available_for_every_platform(self):
        with override_settings(SOCIAL_PUBLIC_BASE_URL="https://app.test", ENV="prod", DEBUG=False):
            for platform in Platform.values:
                self.assertEqual(setup_message(platform), "")
                self.assertFalse(local_youtube_origin(platform))
