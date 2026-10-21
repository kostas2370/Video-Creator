from apps.publishing.platforms import instagram, tiktok, youtube
import io
import tempfile
from datetime import timedelta
from unittest.mock import Mock, patch
from uuid import uuid4

import requests
from django.core.files.base import ContentFile
from django.db import connection
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.usermanagement.baker_recipes import user
from apps.videomanagement.tests.api.base import ApiTestCase

from apps.publishing import oauth, providers, tasks
from apps.publishing.models import OAuthAttempt, Platform, PublishJob, SocialAccount
from apps.publishing.serializers import PublishSerializer
from apps.publishing.services import media_url, validate_options

CONFIG = {platform: {"client_id": "client-id", "client_secret": "app-secret", "api_version": "v25.0"} for platform in Platform.values}
METADATA = {"duration": 10, "fps": 30, "width": 1080, "height": 1920, "audio": True}
CREATOR = {"creator_nickname": "Creator", "privacy_level_options": ["SELF_ONLY", "PUBLIC_TO_EVERYONE"],
           "comment_disabled": False, "duet_disabled": True, "stitch_disabled": False, "max_video_post_duration_sec": 60}


@override_settings(SOCIAL_PUBLIC_BASE_URL="https://app.test", SOCIAL_PUBLISHING=CONFIG)
class PublishingTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        setting = override_settings(MEDIA_ROOT=self.directory.name, PUBLISHING_SNAPSHOT_ROOT=self.directory.name + "/snapshots")
        setting.enable()
        self.addCleanup(setting.disable)
        self.video = self.video_for(status="COMPLETED")
        self.video.output.save("export.mp4", ContentFile(b"export-bytes"))
        self.account = SocialAccount.objects.create(user=self.user, platform="youtube", external_id="channel", display_name="My channel",
                                                    access_token="secret-access", refresh_token="secret-refresh")
        self.metadata = patch("apps.publishing.services.video_metadata", return_value=METADATA).start()
        self.addCleanup(patch.stopall)
        self.queue = patch("apps.publishing.tasks.upload_job.delay").start()

    def payload(self, **changes):
        return {"account": str(self.account.pk), "video": str(self.video.pk), "request_id": str(uuid4()), "export_updated_at": self.video.updated_at.isoformat(),
                "title": "My video", "caption": "A story", "privacy": "private", "made_for_kids": False, "confirmed": True, **changes}

    def post(self, **changes):
        return self.client.post(reverse("publishing-jobs"), self.payload(**changes), format="json")

    def new_job(self, platform="youtube", **changes):
        account = self.account
        if platform != "youtube":
            account, _ = SocialAccount.objects.get_or_create(user=self.user, platform=platform, external_id="creator", defaults={"display_name": "Creator", "access_token": "private-token"})
        serializer = PublishSerializer(data=self.payload())
        serializer.is_valid(raise_exception=True)
        options = {key: value for key, value in serializer.validated_data.items() if key not in ("account", "video", "request_id", "export_updated_at")}
        job = PublishJob.objects.create(user=self.user, video=self.video, account=account, account_name=account.display_name,
                                       platform=platform, request_id=uuid4(), options=options, metadata=METADATA, **changes)
        job.media.save("snapshot.mp4", ContentFile(b"snapshot"))
        return job

    def test_connections_exclude_secrets_and_tokens_are_encrypted(self):
        response = self.client.get(reverse("publishing-connections"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["accounts"][0]["display_name"], "My channel")
        for secret in ("secret-access", "secret-refresh", "app-secret"):
            self.assertNotIn(secret, str(response.data))
        with connection.cursor() as cursor:
            cursor.execute("SELECT access_token FROM publishing_socialaccount WHERE external_id = %s", ["channel"])
            self.assertNotIn("secret-access", cursor.fetchone()[0])

    @override_settings(SOCIAL_PUBLISHING={})
    def test_missing_app_configuration_is_explicit_and_cannot_connect(self):
        response = self.client.get(reverse("publishing-connections"))
        self.assertTrue(all(not row["configured"] for row in response.data["platforms"]))
        response = self.client.post(reverse("publishing-connect", args=["youtube"]), {"video": str(self.video.pk)})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(OAuthAttempt.objects.count(), 0)

    def test_account_ownership_is_enforced(self):
        self.account.user = user.make()
        self.account.save()
        self.assertEqual(self.post().status_code, 404)
        self.assertEqual(self.client.get(reverse("publishing-context", args=[self.account.pk])).status_code, 404)
        self.assertEqual(self.client.delete(reverse("publishing-disconnect", args=[self.account.pk])).status_code, 404)
        self.queue.assert_not_called()

    def test_cannot_publish_another_creators_export(self):
        foreign = self.video_for(owner=user.make(), status="COMPLETED")
        self.assertEqual(self.post(video=str(foreign.pk)).status_code, 404)
        self.queue.assert_not_called()

    def test_requires_an_explicit_confirmation_audience_and_privacy(self):
        for changes in ({"confirmed": False}, {"privacy": ""}, {"title": ""}):
            with self.subTest(changes=changes):
                self.assertEqual(self.post(**changes).status_code, 400)
        payload = self.payload()
        del payload["made_for_kids"]
        self.assertEqual(self.client.post(reverse("publishing-jobs"), payload, format="json").status_code, 400)
        self.queue.assert_not_called()

    def test_only_completed_exports_can_be_sent(self):
        self.video.status = "RENDERING"
        self.video.save()
        self.assertEqual(self.post().status_code, 400)
        self.queue.assert_not_called()

    def test_upload_takes_snapshot_and_duplicate_submission_is_idempotent(self):
        payload = self.payload()
        first = self.client.post(reverse("publishing-jobs"), payload, format="json")
        self.assertEqual(first.status_code, 202, first.data)
        self.video.output.save("new-export.mp4", ContentFile(b"different-export"))
        second = self.client.post(reverse("publishing-jobs"), payload, format="json")
        self.assertEqual(first.data["id"], second.data["id"])
        job = PublishJob.objects.get()
        with job.media.open("rb") as source:
            self.assertEqual(source.read(), b"export-bytes")
        self.queue.assert_called_once()
        self.assertNotIn("media", first.data)
        self.assertNotIn("options", first.data)

    def test_changed_export_cannot_be_published_without_reviewing_it_again(self):
        payload = self.payload()
        self.video.save()
        response = self.client.post(reverse("publishing-jobs"), payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.queue.assert_not_called()

    def test_queue_failure_is_stored_without_uploading(self):
        self.queue.side_effect = RuntimeError("offline")
        response = self.post()
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data["status"], "FAILED")
        self.assertIn("Nothing was sent", response.data["error"])

    def test_disconnect_cancels_queued_jobs_and_hides_local_tokens(self):
        job = self.new_job()
        self.assertEqual(self.client.delete(reverse("publishing-disconnect", args=[self.account.pk])).status_code, 204)
        job.refresh_from_db()
        self.assertEqual(job.status, "FAILED")
        self.assertIsNone(job.account_id)
        self.assertFalse(SocialAccount.objects.exists())

    def test_oauth_is_bound_to_browser_and_consumed_once(self):
        url, browser = oauth.begin(self.user, "youtube", self.video)
        from urllib.parse import parse_qs, urlparse
        state = parse_qs(urlparse(url).query)["state"][0]
        with self.assertRaises(ValidationError):
            oauth.consume("youtube", state, "wrong-browser")
        with self.assertRaises(ValidationError):
            oauth.consume("tiktok", state, browser)
        attempt = oauth.consume("youtube", state, browser)
        self.assertEqual(attempt.user, self.user)
        with self.assertRaises(ValidationError):
            oauth.consume("youtube", state, browser)

    def test_oauth_expiry_and_inactive_users_are_rejected(self):
        from urllib.parse import parse_qs, urlparse
        for inactive in (False, True):
            url, browser = oauth.begin(self.user, "youtube", self.video)
            state = parse_qs(urlparse(url).query)["state"][0]
            if inactive:
                self.user.is_active = False
                self.user.save()
            else:
                OAuthAttempt.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
            with self.assertRaises(ValidationError):
                oauth.consume("youtube", state, browser)

    def test_callback_requires_browser_cookie_and_never_exposes_provider_errors(self):
        self.client.force_authenticate(None)
        with patch("apps.publishing.oauth.finish") as finish:
            response = self.client.get(reverse("publishing-callback", args=["youtube"]), {"state": "forged", "code": "secret-code"})
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("secret-code", response.url)
        finish.assert_not_called()

    def test_oauth_start_sets_a_secure_httponly_binding_cookie(self):
        response = self.client.post(reverse("publishing-connect", args=["youtube"]), {"video": str(self.video.pk)})
        self.assertEqual(response.status_code, 200)
        cookie = response.cookies[oauth.COOKIE_NAME]
        self.assertTrue(cookie["secure"])
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Lax")
        self.assertNotIn("app-secret", response.data["url"])

    def test_refreshing_tokens_uses_server_credentials_without_exposing_them(self):
        self.account.expires_at = timezone.now() - timedelta(seconds=1)
        self.account.save()
        with patch("apps.publishing.providers.api", return_value={"access_token": "refreshed", "expires_in": 3600}) as request:
            token = providers.access_token(self.account)
        self.assertEqual(token, "refreshed")
        self.assertEqual(request.call_args.kwargs["data"]["refresh_token"], "secret-refresh")
        self.account.refresh_from_db()
        self.assertEqual(self.account.access_token, "refreshed")

    def test_upload_task_is_claimed_once_and_does_not_reupload_on_replay(self):
        job = self.new_job()
        def uploaded(job):
            tasks.update(job, status=PublishJob.Status.PROCESSING, remote_id="uploaded")
        with patch("apps.publishing.platforms.youtube.YouTubePublisher.upload", side_effect=uploaded) as upload, patch("apps.publishing.tasks.schedule_status"):
            tasks.upload_job.run(str(job.pk))
            tasks.upload_job.run(str(job.pk))
        upload.assert_called_once()

    def test_uncertain_upload_never_blindly_retries(self):
        job = self.new_job()
        with patch("apps.publishing.platforms.youtube.YouTubePublisher.upload", side_effect=requests.Timeout("sensitive URL")) as upload:
            tasks.upload_job.run(str(job.pk))
            tasks.upload_job.run(str(job.pk))
        job.refresh_from_db()
        self.assertEqual(job.status, "NEEDS_CHECK")
        self.assertNotIn("sensitive", job.error)
        upload.assert_called_once()

    def test_instagram_publish_is_claimed_once_after_container_finishes(self):
        job = self.new_job("instagram", status="PROCESSING", remote_id="container")
        with patch("apps.publishing.platforms.instagram.api", side_effect=[{"status_code": "FINISHED"}, {"id": "posted"}, {"permalink": "https://www.instagram.com/reel/result/"}]) as request:
            tasks.poll_job.run(str(job.pk))
            tasks.poll_job.run(str(job.pk))
        self.assertEqual(sum("media_publish" in call.args[1] for call in request.call_args_list), 1)
        job.refresh_from_db()
        self.assertEqual(job.status, "PUBLISHED")

    def test_uncertain_instagram_publishing_cannot_be_repeated_by_refresh(self):
        job = self.new_job("instagram", status="NEEDS_CHECK", remote_id="container")
        with patch("apps.publishing.views.poll_job.delay") as poll:
            self.client.post(reverse("publishing-refresh", args=[job.pk]))
        poll.assert_not_called()
        job.refresh_from_db()
        self.assertEqual(job.status, "NEEDS_CHECK")

    def test_signed_media_urls_are_bound_to_one_job(self):
        from urllib.parse import parse_qs, urlparse
        job = self.new_job("instagram", status="PROCESSING")
        other = self.new_job("instagram", status="PROCESSING")
        token = parse_qs(urlparse(media_url(job)).query)["token"][0]
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(reverse("publishing-media", args=[job.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("publishing-media", args=[other.pk]), {"token": token}).status_code, 404)
        response = self.client.get(reverse("publishing-media", args=[job.pk]), {"token": token})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"snapshot")

    def test_upload_snapshots_have_no_public_storage_url(self):
        job = self.new_job("instagram")
        with self.assertRaises(ValueError):
            _ = job.media.url
        self.assertIn("/snapshots/", job.media.path)

    def test_tiktok_validates_current_creator_limits_and_interactions(self):
        self.account.platform = "tiktok"
        serializer = PublishSerializer(data=self.payload(privacy="SELF_ONLY", music_consent=True))
        serializer.is_valid(raise_exception=True)
        values = dict(serializer.validated_data)
        validate_options(self.account, values, METADATA, 100, CREATOR)
        for changes in ({"privacy": "unlisted"}, {"music_consent": False}, {"allow_duet": True}, {"branded_content": True}):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                validate_options(self.account, {**values, **changes}, METADATA, 100, CREATOR)
        with self.assertRaises(ValidationError):
            validate_options(self.account, values, {**METADATA, "duration": 61}, 100, CREATOR)

    def test_tiktok_caption_counts_utf16_units(self):
        self.account.platform = "tiktok"
        serializer = PublishSerializer(data=self.payload(privacy="SELF_ONLY", music_consent=True, caption="😀" * 1101))
        serializer.is_valid(raise_exception=True)
        with self.assertRaises(ValidationError):
            validate_options(self.account, serializer.validated_data, METADATA, 100, CREATOR)

    def test_upload_urls_cannot_send_tokens_to_untrusted_hosts(self):
        for url in ("http://www.googleapis.com/upload", "https://evil.test/upload", "https://www.googleapis.com.evil.test/upload", "https://user@www.googleapis.com/upload"):
            with self.subTest(url=url), self.assertRaises(providers.ProviderError):
                providers.checked_upload_url(url, "youtube")
        self.assertEqual(providers.checked_upload_url("https://upload.us.tiktokapis.com/video/", "tiktok"), "https://upload.us.tiktokapis.com/video/")

    def test_tiktok_chunk_plan_merges_trailing_bytes(self):
        for size in (100, 4 * 1024**2, 10 * 1024**2 + 1, 4 * 1024**3):
            chunk, count = tiktok.chunk_plan(size)
            lengths = [chunk] * (count - 1) + [size - chunk * (count - 1)]
            self.assertEqual(sum(lengths), size)
            self.assertLessEqual(max(lengths), 128 * 1024**2)
            self.assertGreaterEqual(count, 1)
            self.assertLessEqual(count, 1000)

    def test_youtube_upload_transfers_snapshot_with_explicit_privacy(self):
        job = self.new_job()
        session = Mock(status_code=200, headers={"Location": "https://www.googleapis.com/upload?upload_id=test"})
        uploaded = Mock(status_code=200)
        uploaded.json.return_value = {"id": "remote-video"}
        def transfer(url, **kwargs):
            self.assertEqual(kwargs["data"].read(), b"snapshot")
            return uploaded
        with patch("apps.publishing.platforms.youtube.requests.post", return_value=session) as start, patch("apps.publishing.platforms.common.requests.put", side_effect=transfer):
            youtube.YouTubePublisher(job.account, "auth-token").upload(job)
        self.assertEqual(start.call_args.kwargs["json"]["status"]["privacyStatus"], "private")
        self.assertEqual(job.remote_id, "remote-video")
        self.assertEqual(job.status, "PROCESSING")

    def test_tiktok_upload_preserves_creator_choices_and_byte_ranges(self):
        job = self.new_job("tiktok")
        job.options.update(privacy="SELF_ONLY", music_consent=True, synthetic=True)
        response = {"data": {"publish_id": "publish-id", "upload_url": "https://open-upload.tiktokapis.com/video/"}}
        with patch("apps.publishing.platforms.tiktok.api", return_value=response) as init, patch("apps.publishing.platforms.tiktok.put_binary") as upload:
            tiktok.TikTokPublisher(job.account, "auth-token").upload(job)
        self.assertEqual(init.call_args.kwargs["json"]["post_info"]["privacy_level"], "SELF_ONLY")
        self.assertTrue(init.call_args.kwargs["json"]["post_info"]["is_aigc"])
        self.assertEqual(upload.call_args.kwargs["data"], b"snapshot")
        self.assertEqual(upload.call_args.kwargs["headers"]["Content-Range"], "bytes 0-7/8")

    def test_youtube_status_marks_processed_upload_published(self):
        job = self.new_job(status="PROCESSING", remote_id="remote-video")
        result = {"items": [{"status": {"uploadStatus": "processed"}}]}
        with patch("apps.publishing.platforms.youtube.api", return_value=result) as request:
            tasks.poll_once(job)
        self.assertEqual(request.call_args.kwargs["params"]["id"], "remote-video")
        self.assertEqual(request.call_args.kwargs["token"], job.account.access_token)
        job.refresh_from_db()
        self.assertEqual(job.status, "PUBLISHED")

    def test_publisher_requires_both_upload_and_status_methods(self):
        from apps.publishing.platforms.base import Publisher

        class UploadOnly(Publisher):
            def upload(self, job):
                pass

        with self.assertRaises(TypeError):
            UploadOnly(None, "token")

    def test_private_tiktok_completion_does_not_invent_a_public_url(self):
        job = self.new_job("tiktok", status="PROCESSING", remote_id="publish-id")
        with patch("apps.publishing.platforms.tiktok.api", return_value={"data": {"status": "PUBLISH_COMPLETE", "publicaly_available_post_id": []}}):
            tasks.poll_once(job)
        self.assertEqual(job.status, "PUBLISHED")
        self.assertEqual(job.url, "")

    def test_instagram_initialization_uses_signed_snapshot_not_a_user_supplied_url(self):
        job = self.new_job("instagram")
        with patch("apps.publishing.platforms.instagram.api", return_value={"id": "container"}) as init:
            instagram.InstagramPublisher(job.account, "auth-token").upload(job)
        source = init.call_args.kwargs["data"]["video_url"]
        self.assertTrue(source.startswith("https://app.test/api/publishing/media/"))
        self.assertNotIn("private-token", source)
        self.assertEqual(job.remote_id, "container")

    def test_provider_errors_do_not_leak_response_bodies(self):
        response = Mock(status_code=400)
        response.json.return_value = {"error": "secret-access"}
        with patch("apps.publishing.providers.requests.request", return_value=response):
            with self.assertRaises(providers.ProviderError) as caught:
                providers.api("GET", "https://www.googleapis.com/test", "secret-access")
        self.assertNotIn("secret-access", str(caught.exception))

    def test_successful_callback_saves_to_the_initiating_creator_only(self):
        from urllib.parse import parse_qs, urlparse
        url, browser = oauth.begin(self.user, "youtube", self.video)
        state = parse_qs(urlparse(url).query)["state"][0]
        self.client.force_authenticate(None)
        self.client.cookies[oauth.COOKIE_NAME] = browser
        with patch("apps.publishing.oauth.exchange_code", return_value={"access_token": "new-secret", "refresh_token": "new-refresh", "expires_in": 3600}), patch("apps.publishing.oauth.identities", return_value=[{"external_id": "another-channel", "display_name": "New channel", "access_token": "new-secret"}]):
            response = self.client.get(reverse("publishing-callback", args=["youtube"]), {"state": state, "code": "code"})
        self.assertIn("publishing=connected", response.url)
        self.assertEqual(SocialAccount.objects.get(external_id="another-channel").user, self.user)

    def test_signed_media_supports_byte_ranges_for_platform_fetchers(self):
        from urllib.parse import parse_qs, urlparse
        job = self.new_job("instagram")
        token = parse_qs(urlparse(media_url(job)).query)["token"][0]
        self.client.force_authenticate(None)
        response = self.client.get(reverse("publishing-media", args=[job.pk]), {"token": token}, HTTP_RANGE="bytes=1-3")
        self.assertEqual(response.status_code, 206)
        self.assertEqual(response["Content-Range"], "bytes 1-3/8")
        self.assertEqual(b"".join(response.streaming_content), b"nap")
        response = self.client.get(reverse("publishing-media", args=[job.pk]), {"token": token}, HTTP_RANGE="bytes=20-30")
        self.assertEqual(response.status_code, 416)
