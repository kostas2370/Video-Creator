import tempfile
from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

from asgiref.sync import async_to_sync
from django.core.cache import caches
from django.core.files.base import ContentFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.common.tests.test_r2_storage import MemoryR2
from apps.usermanagement.baker_recipes import user
from apps.videomanagement.models import VideoShare
from apps.videomanagement.throttling import (
    PublicShareMediaThrottle,
    PublicShareMetadataThrottle,
)

from .base import ApiTestCase


async def response_body(response):
    return b"".join([chunk async for chunk in response.streaming_content])


@override_settings(
    R2_STORAGE_ENABLED=False,
    CACHES={
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
        "public_shares": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "video-sharing-tests",
        },
    },
)
class VideoSharingTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        caches["public_shares"].clear()
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        media = override_settings(MEDIA_ROOT=directory.name)
        media.enable()
        self.addCleanup(media.disable)
        self.video = self.video_for(
            output=ContentFile(b"0123456789", name="shared.mp4"),
            title="Ocean stories",
            description="A little story.\nA second line.",
            tags={"youtube": ["ocean", "wildlife"], "tiktok": ["ocean"]},
            notes="Private editor notes",
        )
        self.url = reverse("video-share", args=[self.video.pk])
        self.public = APIClient()

    def create_link(self, days=None):
        response = self.client.post(self.url, {"expires_in_days": days}, format="json")
        self.assertEqual(response.status_code, 200)
        return VideoShare.objects.get(video=self.video)

    def public_urls(self, token):
        return [
            reverse(name, args=[token])
            for name in ("shared-video", "shared-video-media")
        ]

    def test_sharing_defaults_off_and_requires_an_export(self):
        self.assertEqual(
            self.client.get(self.url).json(),
            {
                "active": False,
                "path": None,
                "expires_at": None,
                "expiry_options": [
                    {"value": None, "label": "Never"},
                    *(
                        {"value": value, "label": label}
                        for value, label in VideoShare.ExpiryDays.choices
                    ),
                ],
            },
        )
        self.video.output = ""
        self.video.save(update_fields=["output"])
        self.assertEqual(self.client.post(self.url, {}, format="json").status_code, 400)
        self.assertFalse(VideoShare.objects.exists())

    def test_public_metadata_limits_are_per_ip_across_links_and_separate_from_media(
        self,
    ):
        share = self.create_link()
        url, media = self.public_urls(share.token)
        with patch.object(PublicShareMetadataThrottle, "rate", "2/minute"):
            for _ in range(2):
                self.assertEqual(self.public.get(url).status_code, 200)
            response = self.public.get(self.public_urls(uuid4())[0])
            self.assertEqual(response.status_code, 429)
            self.assertGreater(int(response["Retry-After"]), 0)
            self.assertIn("no-store", response["Cache-Control"])
            self.assertEqual(
                self.public.get(url, REMOTE_ADDR="198.51.100.2").status_code, 200
            )
            self.assertEqual(self.public.head(media).status_code, 200)

    def test_public_media_limits_count_head_and_ranges_without_blocking_metadata(self):
        share = self.create_link()
        url, media = self.public_urls(share.token)
        with patch.object(PublicShareMediaThrottle, "rate", "2/minute"):
            self.assertEqual(self.public.head(media).status_code, 200)
            response = self.public.get(media, HTTP_RANGE="bytes=2-5")
            self.assertEqual(response.status_code, 206)
            self.assertEqual(async_to_sync(response_body)(response), b"2345")
            self.assertEqual(self.public.get(media).status_code, 429)
            self.assertEqual(self.public.get(url).status_code, 200)

    def test_only_owner_can_manage_links(self):
        self.client.force_authenticate(user.make())
        for method in ("get", "post", "delete"):
            self.assertEqual(getattr(self.client, method)(self.url).status_code, 404)
        self.client.force_authenticate(None)
        for method in ("get", "post", "delete"):
            self.assertIn(
                getattr(self.client, method)(self.url).status_code, (401, 403)
            )
        self.assertFalse(VideoShare.objects.exists())

    def test_creation_is_idempotent_and_expiry_is_validated(self):
        before = timezone.now()
        share = self.create_link(7)
        self.assertTrue(
            before + timedelta(days=7)
            <= share.expires_at
            <= timezone.now() + timedelta(days=7)
        )
        self.assertEqual(self.create_link().token, share.token)
        self.assertEqual(
            self.client.post(
                self.url, {"expires_in_days": -1}, format="json"
            ).status_code,
            400,
        )
        self.assertEqual(self.client.get(self.url)["Cache-Control"], "no-store")

    def test_public_metadata_is_an_explicit_allowlist_and_ignores_stale_auth(self):
        share = self.create_link()
        url, media = self.public_urls(share.token)
        response = self.public.get(url, HTTP_AUTHORIZATION="Bearer invalid")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "title": "Ocean stories",
                "description": self.video.description,
                "tags": ["ocean", "wildlife"],
                "media_url": "http://testserver" + media,
            },
        )
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(response["Referrer-Policy"], "no-referrer")
        self.assertEqual(response["X-Robots-Tag"], "noindex, nofollow")

    def test_revocation_blocks_metadata_and_media_and_new_link_has_a_new_token(self):
        share = self.create_link()
        self.assertEqual(self.client.delete(self.url).status_code, 204)
        self.assertEqual(self.client.delete(self.url).status_code, 204)
        for url in self.public_urls(share.token):
            self.assertEqual(self.public.get(url).status_code, 404)
            self.assertEqual(self.public.head(url).status_code, 404)
        self.assertNotEqual(self.create_link().token, share.token)

    def test_expired_missing_and_unexported_links_are_unavailable(self):
        share = self.create_link()
        VideoShare.objects.filter(pk=share.pk).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )
        for token, status in ((share.token, 410), (uuid4(), 404)):
            for url in self.public_urls(token):
                response = self.public.get(url)
                self.assertEqual(response.status_code, status)
                self.assertEqual(self.public.head(url).status_code, status)
                self.assertIn("no-store", response["Cache-Control"])
                if status == 410:
                    self.assertEqual(
                        response.json(),
                        {
                            "detail": "This share link has expired. Ask the creator for a new link."
                        },
                    )
        self.assertFalse(self.client.get(self.url).json()["active"])
        renewed = self.create_link(1)
        self.assertNotEqual(renewed.token, share.token)
        self.video.output = ""
        self.video.save(update_fields=["output"])
        for url in self.public_urls(renewed.token):
            self.assertEqual(self.public.get(url).status_code, 404)

    def test_only_the_finished_output_is_shared_and_latest_saved_details_are_visible(
        self,
    ):
        share = self.create_link()
        self.video.title = "Updated story"
        self.video.save(update_fields=["title"])
        url, media = self.public_urls(share.token)
        self.assertEqual(self.public.get(url).json()["title"], "Updated story")
        self.assertEqual(
            self.public.get(media + "?path=../private.mp4").status_code, 200
        )
        self.assertIn(
            self.public.get(self.video.output.url).status_code, (401, 403, 404)
        )
        self.assertEqual(self.public.post(url).status_code, 405)
        self.assertEqual(
            self.public.get(reverse("shared-video", args=[self.video.pk])).status_code,
            404,
        )

    def test_media_supports_head_full_playback_and_ranges(self):
        share = self.create_link()
        _, media = self.public_urls(share.token)
        head = self.public.head(media)
        self.assertEqual(head.status_code, 200)
        self.assertEqual(head["Content-Length"], "10")
        self.assertEqual(head["Content-Type"], "video/mp4")
        response = self.public.get(media)
        self.assertEqual(async_to_sync(response_body)(response), b"0123456789")
        response = self.public.get(media, HTTP_RANGE="bytes=2-5")
        self.assertEqual(response.status_code, 206)
        self.assertEqual(response["Content-Range"], "bytes 2-5/10")
        self.assertEqual(async_to_sync(response_body)(response), b"2345")
        self.assertEqual(
            self.public.get(media, HTTP_RANGE="bytes=999-").status_code, 416
        )

    def test_missing_stored_media_returns_404(self):
        share = self.create_link()
        self.video.output.storage.delete(self.video.output.name)
        self.assertEqual(
            self.public.head(self.public_urls(share.token)[1]).status_code, 404
        )

    @override_settings(
        R2_STORAGE_ENABLED=True,
        R2_ACCOUNT_ID="a" * 32,
        R2_BUCKET_NAME="test-bucket",
        R2_ACCESS_KEY_ID="test",
        R2_SECRET_ACCESS_KEY="test",
        R2_JURISDICTION="",
    )
    def test_r2_playback_uses_private_storage_and_supports_seeking(self):
        archive = MemoryR2()
        with patch("apps.common.r2_storage._archive", return_value=archive):
            self.video.output.save("remote.mp4", ContentFile(b"abcdefghij"))
            share = self.create_link()
            media = self.public_urls(share.token)[1]
            response = self.public.get(media, HTTP_RANGE="bytes=4-7")
            self.assertEqual(response.status_code, 206)
            self.assertEqual(async_to_sync(response_body)(response), b"efgh")
            self.assertNotIn("X-Accel-Redirect", response)
            self.client.delete(self.url)
            self.assertEqual(self.public.get(media).status_code, 404)

    def test_deleting_video_invalidates_the_link(self):
        share = self.create_link()
        self.video.delete()
        self.assertFalse(VideoShare.objects.filter(pk=share.pk).exists())
        for url in self.public_urls(share.token):
            self.assertEqual(self.public.get(url).status_code, 404)
