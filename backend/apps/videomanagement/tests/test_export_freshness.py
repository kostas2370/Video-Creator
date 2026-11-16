from django.test import TestCase
from model_bakery import baker

from apps.videomanagement.baker_recipes import scene, video, scene_image
from apps.videomanagement.models import Music, MusicCatalogTrack, Video
from apps.videomanagement.serializers.models import VideoNestedSerializer
from apps.videomanagement.services.videos.export_freshness import (
    export_freshness,
    export_source_key,
)


class ExportFreshnessTests(TestCase):
    def setUp(self):
        self.video = video.make(output="media/output/export.mp4")
        self.scene = scene.make(video=self.video)
        scene_image.make(scene=self.scene)
        self.video.export_source_key = export_source_key(self.video)
        self.video.save(update_fields=["export_source_key"])

    def test_saved_edit_changes_and_undo_are_detected(self):
        self.assertEqual(export_freshness(self.video)["status"], "current")
        self.scene.pause_after = 1
        self.scene.save()
        self.assertEqual(export_freshness(self.video)["status"], "stale")
        self.scene.pause_after = 0
        self.scene.save()
        self.assertEqual(export_freshness(self.video)["status"], "current")

    def test_notes_and_publishing_metadata_do_not_change_the_export(self):
        self.video.notes = "Remember to share"
        self.video.title = "A new publishing title"
        self.video.tags = {"tags": ["new"]}
        self.video.save()
        self.assertEqual(export_freshness(self.video)["status"], "current")

    def test_music_and_scene_order_change_freshness(self):
        self.video.music = baker.make(Music, name="Music", file="music.mp3")
        self.assertEqual(export_freshness(self.video)["status"], "stale")
        self.video.music = None
        second = scene.make(video=self.video)
        self.video.export_source_key = export_source_key(self.video)
        self.scene.position = 3
        self.scene.save()
        self.assertEqual(export_freshness(self.video)["status"], "stale")
        second.delete()

    def test_legacy_exports_are_unknown_and_unexported_projects_have_no_export(self):
        self.video.export_source_key = ""
        self.assertEqual(export_freshness(self.video)["status"], "unknown")
        self.video.output = ""
        self.assertEqual(export_freshness(self.video)["status"], "none")

    def test_editor_response_preserves_music_id_and_adds_read_only_details(self):
        track = baker.make(
            MusicCatalogTrack,
            title="Quiet piano",
            metadata={"channel_title": "Composer"},
            license_url="https://example.test/license",
            attribution="Credit Composer",
        )
        self.video.music = baker.make(
            Music, name="song-file", file="media/music/song.mp3", catalog_track=track
        )
        self.video.save(update_fields=["music"])
        loaded = Video.objects.with_editor_media().get(pk=self.video.pk)
        data = VideoNestedSerializer(loaded).data
        self.assertEqual(str(data["music"]), str(self.video.music_id))
        self.assertEqual(data["music_details"]["title"], "Quiet piano")
        self.assertEqual(data["music_details"]["artist"], "Composer")
        self.assertEqual(data["music_details"]["license_url"], track.license_url)
        self.assertEqual(data["export_freshness"]["status"], "stale")
