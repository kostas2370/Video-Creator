import tempfile
import wave
from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse

from apps.usermanagement.baker_recipes import user
from apps.videomanagement.models import MediaAsset

from .base import ApiTestCase


class SharedMusicTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        override = override_settings(MEDIA_ROOT=directory.name)
        override.enable()
        self.addCleanup(override.disable)
        self.url = reverse("mediaasset-list")

    def audio(self):
        data = BytesIO()
        with wave.open(data, "wb") as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(8000)
            stream.writeframes(b"\0\0" * 8000)
        return SimpleUploadedFile(
            "track.wav", data.getvalue(), content_type="audio/wav"
        )

    def shared(self, **values):
        return MediaAsset.objects.create(
            title="General music",
            kind="AUDIO",
            file=self.audio(),
            is_shared=True,
            license_url="https://example.com/license",
            **{"catalog_approved": True, **values},
        )

    def test_lists_own_private_media_and_approved_general_music_only(self):
        own = MediaAsset.objects.create(
            created_by=self.user, title="Private", kind="AUDIO", file=self.audio()
        )
        foreign = MediaAsset.objects.create(
            created_by=user.make(),
            title="Other user's track",
            kind="AUDIO",
            file=self.audio(),
        )
        shared = self.shared()
        pending = self.shared(catalog_approved=False)
        missing = self.shared()
        missing.file = ""
        missing.save()
        response = self.client.get(self.url)
        self.assertEqual(
            {row["id"] for row in response.data["results"]},
            {str(own.pk), str(shared.pk)},
        )
        for hidden in (foreign, pending, missing):
            self.assertEqual(
                self.client.get(
                    reverse("mediaasset-detail", args=[hidden.pk])
                ).status_code,
                404,
            )
        self.assertEqual(
            self.client.get(self.url, {"scope": "private"}).data["count"], 1
        )
        self.assertEqual(
            self.client.get(self.url, {"scope": "shared"}).data["count"], 1
        )
        self.assertEqual(
            self.client.get(self.url, {"scope": "unknown"}).status_code, 400
        )

    def test_shared_music_can_be_used_but_cannot_be_edited_or_removed(self):
        asset = self.shared()
        video = self.video_for(status="READY")
        response = self.client.post(
            reverse("mediaasset-use", args=[asset.pk]),
            {"video_id": str(video.pk), "purpose": "music"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        video.refresh_from_db()
        self.assertTrue(video.music.file)
        url = reverse("mediaasset-detail", args=[asset.pk])
        self.assertEqual(
            self.client.patch(url, {"title": "Changed"}, format="json").status_code, 403
        )
        self.assertEqual(self.client.delete(url).status_code, 403)
        self.client.force_authenticate(user.make())
        self.assertEqual(self.client.get(url).status_code, 200)
        response = self.client.get(reverse("mediaasset-download", args=[asset.pk]))
        self.assertEqual(response.status_code, 200)
        response.close()

    def test_uploads_cannot_publish_themselves_as_general_music(self):
        response = self.client.post(
            self.url,
            {
                "title": "Private upload",
                "file": self.audio(),
                "is_shared": True,
                "catalog_approved": True,
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 201, response.data)
        asset = MediaAsset.objects.get(pk=response.data["id"])
        self.assertEqual(asset.created_by, self.user)
        self.assertFalse(asset.is_shared)
        self.assertFalse(asset.catalog_approved)

    def test_approval_requires_audio_and_license_information(self):
        asset = MediaAsset(
            title="Pending", kind="AUDIO", is_shared=True, catalog_approved=True
        )
        with self.assertRaises(ValidationError) as error:
            asset.clean()
        self.assertEqual(set(error.exception.message_dict), {"file", "license_url"})
