import tempfile
import wave
from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse

from apps.usermanagement.baker_recipes import user
from apps.videomanagement.models import MediaAsset, MusicCatalogTrack

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
        self.catalog_url = reverse("musiccatalogtrack-list")

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
        return MusicCatalogTrack.objects.create(
            source_id=f"test:{MusicCatalogTrack.objects.count()}",
            title="General music",
            category="fun",
            file=self.audio(),
            source_url="https://example.com/track",
            license_url="https://example.com/license",
            **{"approved": True, **values},
        )

    def test_private_media_and_catalog_are_stored_and_listed_separately(self):
        own = MediaAsset.objects.create(
            created_by=self.user, title="Private", kind="AUDIO", file=self.audio()
        )
        foreign = MediaAsset.objects.create(
            created_by=user.make(), title="Other track", kind="AUDIO", file=self.audio()
        )
        shared = self.shared()
        pending = self.shared(approved=False)
        missing = self.shared()
        missing.file = ""
        missing.save()
        response = self.client.get(self.url)
        self.assertEqual([row["id"] for row in response.data["results"]], [str(own.pk)])
        response = self.client.get(self.catalog_url)
        self.assertEqual(
            [row["id"] for row in response.data["results"]], [str(shared.pk)]
        )
        self.assertTrue(response.data["results"][0]["is_shared"])
        self.assertEqual(response.data["results"][0]["kind"], "AUDIO")
        for hidden in (pending, missing):
            self.assertEqual(
                self.client.get(
                    reverse("musiccatalogtrack-detail", args=[hidden.pk])
                ).status_code,
                404,
            )
        self.assertEqual(
            self.client.get(
                reverse("mediaasset-detail", args=[foreign.pk])
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(reverse("mediaasset-detail", args=[shared.pk])).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(self.catalog_url, {"category": "horror"}).data["count"], 0
        )
        self.assertEqual(
            self.client.get(self.catalog_url, {"search": "General"}).data["count"], 1
        )

    def test_shared_music_can_be_used_but_cannot_be_edited_or_removed(self):
        track = self.shared()
        video = self.video_for(status="READY")
        response = self.client.post(
            reverse("musiccatalogtrack-use", args=[track.pk]),
            {"video_id": str(video.pk), "purpose": "music"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        video.refresh_from_db()
        self.assertTrue(video.music.file)
        self.assertNotEqual(video.music.file.name, track.file.name)
        self.assertFalse(MediaAsset.objects.exists())
        url = reverse("musiccatalogtrack-detail", args=[track.pk])
        self.assertEqual(
            self.client.patch(url, {"title": "Changed"}, format="json").status_code, 405
        )
        self.assertEqual(self.client.delete(url).status_code, 405)
        self.assertEqual(
            self.client.post(
                self.catalog_url, {"title": "New"}, format="json"
            ).status_code,
            405,
        )
        self.client.force_authenticate(user.make())
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(
            self.client.post(
                reverse("musiccatalogtrack-use", args=[track.pk]),
                {"video_id": str(video.pk), "purpose": "music"},
                format="json",
            ).status_code,
            404,
        )
        response = self.client.get(
            reverse("musiccatalogtrack-download", args=[track.pk])
        )
        self.assertEqual(response.status_code, 200)
        response.close()

    def test_uploads_cannot_create_or_publish_catalog_tracks(self):
        response = self.client.post(
            self.url,
            {
                "title": "Private upload",
                "file": self.audio(),
                "is_shared": True,
                "approved": True,
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(
            MediaAsset.objects.get(pk=response.data["id"]).created_by, self.user
        )
        self.assertFalse(MusicCatalogTrack.objects.exists())

    def test_approval_requires_audio_and_license_information(self):
        track = MusicCatalogTrack(title="Pending", approved=True)
        with self.assertRaises(ValidationError) as error:
            track.clean()
        self.assertEqual(set(error.exception.message_dict), {"file", "license_url"})

    def test_catalog_use_rejects_visual_purposes_and_rendering_projects(self):
        track = self.shared()
        video = self.video_for(status="READY")
        url = reverse("musiccatalogtrack-use", args=[track.pk])
        self.assertEqual(
            self.client.post(
                url, {"video_id": str(video.pk), "purpose": "new_scene"}, format="json"
            ).status_code,
            400,
        )
        video.status = "RENDERING"
        video.save()
        self.assertEqual(
            self.client.post(
                url, {"video_id": str(video.pk), "purpose": "music"}, format="json"
            ).status_code,
            409,
        )
