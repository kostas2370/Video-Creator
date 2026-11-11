import tempfile
import wave
from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse

from apps.usermanagement.baker_recipes import user
from apps.videomanagement.models import MediaAsset, MusicCatalogTrack
from apps.videomanagement.services.media.catalog import (
    select_music_track,
    create_catalog_music,
)

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
            file=self.audio(),
            source_url="https://example.com/track",
            **{
                "title": "General music",
                "category": "fun",
                "license_url": "https://example.com/license",
                "approved": True,
                **values,
            },
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
        self.assertEqual(video.music.name, "general-music")
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

    def test_auto_selection_matches_each_topic_and_defaults_to_general_music(self):
        examples = {
            "educational": "science lesson",
            "suspense": "detective mystery",
            "fun": "happy comedy",
            "horror": "haunted ghost",
            "commercial": "product advertisement",
            "general": "a day in my life",
        }
        for category in examples:
            self.shared(title=category, category=category)
        video = self.video_for(status="READY", title="My project", genre="")
        for category, prompt in examples.items():
            with self.subTest(category=category):
                video.prompt.prompt = prompt
                video.prompt.save()
                self.assertEqual(select_music_track(video).category, category)

    def test_auto_selection_uses_tags_within_the_matching_category(self):
        self.shared(title="Other", category="general", tags=["guitar"])
        expected = self.shared(
            title="Ocean", category="general", tags=["ocean", "piano"]
        )
        video = self.video_for(status="READY", title="Ocean piano", genre="")
        video.prompt.prompt = "Ocean piano"
        self.assertEqual(select_music_track(video), expected)

    def test_auto_select_adds_music_and_chooses_an_alternative_on_repeat(self):
        first = self.shared(title="Calm One", category="general")
        second = self.shared(title="Calm Two", category="general")
        video = self.video_for(status="READY", title="Calm", genre="")
        url = reverse("musiccatalogtrack-auto-select")
        response = self.client.post(url, {"video_id": str(video.pk)}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        selected_id = response.data["track"]["id"]
        video.refresh_from_db()
        self.assertTrue(video.music.file.storage.exists(video.music.file.name))
        self.assertEqual(video.music.created_by, self.user)
        response = self.client.post(url, {"video_id": str(video.pk)}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertNotEqual(response.data["track"]["id"], selected_id)
        self.assertEqual(
            {selected_id, response.data["track"]["id"]}, {str(first.pk), str(second.pk)}
        )
        self.assertFalse(MediaAsset.objects.exists())

    def test_auto_select_rejects_unavailable_tracks_and_keeps_existing_music(self):
        self.shared(approved=False)
        self.shared(license_url="")
        missing = self.shared()
        missing.file.storage.delete(missing.file.name)
        video = self.video_for(status="READY")
        original = video.music_id
        response = self.client.post(
            reverse("musiccatalogtrack-auto-select"),
            {"video_id": str(video.pk)},
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("No general music", str(response.data))
        video.refresh_from_db()
        self.assertEqual(video.music_id, original)

    def test_auto_select_only_changes_owned_editable_videos(self):
        self.shared()
        url = reverse("musiccatalogtrack-auto-select")
        foreign = self.video_for(owner=user.make(), status="READY")
        self.assertEqual(
            self.client.post(
                url, {"video_id": str(foreign.pk)}, format="json"
            ).status_code,
            404,
        )
        locked = self.video_for(status="RENDERING")
        self.assertEqual(
            self.client.post(
                url, {"video_id": str(locked.pk)}, format="json"
            ).status_code,
            409,
        )
        self.assertEqual(self.client.post(url, {}, format="json").status_code, 400)

    def test_generation_copies_catalog_audio_without_changing_the_source(self):
        track = self.shared()
        music = create_catalog_music(track, user=self.user)
        self.assertEqual(music.created_by, self.user)
        self.assertEqual(music.name, track.title)
        self.assertNotEqual(music.file.name, track.file.name)
        with music.file.open("rb") as copied, track.file.open("rb") as source:
            self.assertEqual(copied.read(), source.read())
