import io
import tempfile

from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from model_bakery import baker
from PIL import Image

from apps.series.models import CharacterReference, VideoSeries
from apps.usermanagement.models import User
from apps.videomanagement.models import MediaAsset, Scene, SceneImage, Video
from apps.videomanagement.services.media.references import archive_reference


class ReferenceAssetTests(TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        storage = override_settings(MEDIA_ROOT=folder.name)
        storage.enable()
        self.addCleanup(storage.disable)
        self.user = baker.make(User)
        output = io.BytesIO()
        Image.new("RGB", (16, 16), "orange").save(output, format="PNG")
        self.image = output.getvalue()

    def test_character_upload_is_durable_and_owner_scoped(self):
        reference = CharacterReference.objects.create(created_by=self.user, name="Milo")
        reference.image.save("milo.png", ContentFile(self.image))
        asset = MediaAsset.objects.get(created_by=self.user)
        self.assertIn("character reference", asset.tags)
        reference.image.delete()
        with asset.file.open("rb") as saved:
            self.assertEqual(saved.read(), self.image)

    def test_video_and_series_references_are_archived_without_duplicates(self):
        for model in (Video, VideoSeries):
            target = baker.make(model, created_by=self.user)
            target.reference_image.save("reference.png", ContentFile(self.image))
            archive_reference(target)
            target.save()
        self.assertEqual(MediaAsset.objects.filter(created_by=self.user).count(), 1)
        other = baker.make(User)
        target = baker.make(Video, created_by=other)
        target.reference_image.save("reference.png", ContentFile(self.image))
        self.assertEqual(MediaAsset.objects.filter(created_by=other).count(), 1)

    def test_generated_asset_path_reuses_the_same_asset_when_attached_to_a_scene(self):
        asset = MediaAsset.from_visual(
            user=self.user, upload=ContentFile(self.image, name="image.png"),
            title="Generated image", tags=["ai image"], kind="IMAGE",
        )
        video = baker.make(Video, created_by=self.user)
        scene = baker.make(Scene, video=video)
        visual = SceneImage.objects.create(scene=scene, file=asset.file.path)
        self.assertEqual(visual.asset_id, asset.pk)
        self.assertEqual(MediaAsset.objects.count(), 1)

    def test_backfill_recovers_unlinked_images_from_an_earlier_failed_job(self):
        from pathlib import Path
        from django.conf import settings
        from django.core.management import call_command

        directory = Path(settings.MEDIA_ROOT, "project", "images")
        directory.mkdir(parents=True)
        (directory / "old-starting-image.png").write_bytes(self.image)
        video = baker.make(Video, created_by=self.user, dir_name=str(directory.parent))
        for _ in range(2):
            call_command("archive_reference_images", stdout=io.StringIO())
        asset = MediaAsset.objects.get(created_by=self.user)
        self.assertEqual(asset.source_video_id, video.pk)
        with asset.file.open("rb") as saved:
            self.assertEqual(saved.read(), self.image)
