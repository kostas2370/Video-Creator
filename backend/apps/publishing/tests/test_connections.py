from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from apps.publishing.connections import get_connection, meta, tiktok, youtube
from apps.publishing.diagnostics import log_failure
from apps.publishing.http import ProviderError
from apps.publishing.models import Platform

CONFIG = {platform: {"client_id": "client-id", "client_secret": "secret", "api_version": "v25.0"} for platform in Platform.values}


@override_settings(SOCIAL_PUBLIC_BASE_URL="https://app.test", SOCIAL_PUBLISHING=CONFIG)
class ConnectionTests(SimpleTestCase):
    def test_authorization_preserves_state_callback_and_platform_parameters(self):
        for platform, client_field, scope in (
            (Platform.YOUTUBE, "client_id", "https://www.googleapis.com/auth/youtube.upload"),
            (Platform.TIKTOK, "client_key", "video.publish"),
            (Platform.INSTAGRAM, "client_id", "instagram_content_publish"),
        ):
            with self.subTest(platform=platform):
                url = get_connection(platform).authorization_url("browser-state")
                params = parse_qs(urlparse(url).query)
                self.assertEqual(params["state"], ["browser-state"])
                self.assertEqual(params[client_field], ["client-id"])
                self.assertEqual(params["redirect_uri"], [f"https://app.test/api/publishing/oauth/{platform}/callback/"])
                self.assertIn(scope, params["scope"][0])
                self.assertNotIn("secret", url)

    def test_code_exchange_and_refresh_use_the_correct_client_field(self):
        for module, platform, client_field in (
            (youtube, Platform.YOUTUBE, "client_id"),
            (tiktok, Platform.TIKTOK, "client_key"),
        ):
            with self.subTest(platform=platform), patch.object(module, "request_json", return_value={"access_token": "token"}) as request:
                module.exchange_code("auth-code")
                payload = request.call_args.kwargs["data"]
                self.assertEqual(payload[client_field], "client-id")
                self.assertEqual(payload["code"], "auth-code")
                self.assertEqual(payload["redirect_uri"], f"https://app.test/api/publishing/oauth/{platform}/callback/")
                module.refresh_token("refresh")
                payload = request.call_args.kwargs["data"]
                self.assertEqual(payload[client_field], "client-id")
                self.assertEqual(payload["refresh_token"], "refresh")
                self.assertEqual(payload["grant_type"], "refresh_token")

    def test_meta_exchanges_short_token_for_long_lived_token(self):
        with patch.object(meta, "request_json", side_effect=[{"access_token": "short"}, {"access_token": "long"}]) as request:
            self.assertEqual(meta.exchange_code("code"), {"access_token": "long"})
        self.assertEqual(request.call_args_list[0].kwargs["params"]["code"], "code")
        self.assertEqual(request.call_args.kwargs["params"]["fb_exchange_token"], "short")

    def test_youtube_requires_one_channel_and_tiktok_reads_creator_identity(self):
        with patch.object(youtube, "request_json", return_value={"items": []}):
            with self.assertRaises(ProviderError):
                youtube.identities({"access_token": "token"})
        with patch.object(youtube, "request_json", return_value={"items": [{"id": "channel", "snippet": {"title": "Creator"}}]}):
            self.assertEqual(youtube.identities({"access_token": "token"})[0]["external_id"], "channel")
        with patch.object(tiktok, "request_json", return_value={"data": {"user": {"open_id": "creator", "display_name": "Creator"}}}):
            self.assertEqual(tiktok.identities({"access_token": "token"})[0]["external_id"], "creator")

    def test_meta_pagination_keeps_tokens_on_the_graph_host(self):
        first = {"data": [], "paging": {"next": "https://untrusted.test/?token=secret", "cursors": {"after": "cursor"}}}
        second = {"data": [{"name": "Page", "access_token": "page-token", "instagram_business_account": {"id": "instagram", "username": "creator"}}]}
        with patch.object(meta, "request_json", side_effect=[first, second]) as request:
            profiles = meta.identities({"access_token": "user-token"})
        self.assertEqual(profiles, [{"external_id": "instagram", "display_name": "creator", "access_token": "page-token"}])
        self.assertEqual(request.call_args.args[1], "https://graph.facebook.com/v25.0/me/accounts")
        self.assertEqual(request.call_args.kwargs["params"]["after"], "cursor")

    def test_failure_logs_exclude_exception_messages_and_tracebacks(self):
        with self.assertLogs("apps.publishing", level="WARNING") as logs:
            log_failure("upload", platform="youtube", reference="job-id", error=ProviderError("token=secret https://secret.test"))
        self.assertIn("upload", logs.output[0])
        self.assertIn("job-id", logs.output[0])
        self.assertIn("ProviderError", logs.output[0])
        self.assertNotIn("secret", logs.output[0])
        self.assertIsNone(logs.records[0].exc_info)
