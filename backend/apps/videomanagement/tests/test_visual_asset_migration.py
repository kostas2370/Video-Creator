import tempfile
from importlib import import_module
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from django.core.files.base import ContentFile
from django.db import connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase, override_settings
from PIL import Image

from apps.usermanagement.baker_recipes import user
from apps.videomanagement.baker_recipes import video
from apps.videomanagement.exceptions import GenerationQueueUnavailable
from apps.videomanagement.models import MediaAsset, Scene, SceneImage
from apps.videomanagement.services.videos.jobs import queue_video_generation


class VisualAssetMigrationTests(TransactionTestCase):
    migrate_from = [("videomanagement", "0037_video_is_favorite")]
    migrate_to = [("videomanagement", "0039_backfill_visual_assets")]

    def image(self, color):
        data = BytesIO()
        Image.new("RGB", (16, 16), color).save(data, format="PNG")
        return ContentFile(data.getvalue(), name=f"{color}.png")

    def test_existing_visuals_are_linked_without_moving_files_and_reruns_are_safe(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        override = override_settings(MEDIA_ROOT=directory.name)
        override.enable()
        self.addCleanup(override.disable)
        owner, other_owner = user.make(_quantity=2)
        executor = MigrationExecutor(connection)
        leaves = executor.loader.graph.leaf_nodes()
        self.addCleanup(lambda: MigrationExecutor(connection).migrate(leaves))
        executor.migrate(self.migrate_from)
        old = executor.loader.project_state(self.migrate_from).apps
        Video = old.get_model("videomanagement", "Video")
        Prompt = old.get_model("videomanagement", "UserPrompt")
        Scene = old.get_model("videomanagement", "Scene")
        Visual = old.get_model("videomanagement", "SceneImage")
        Asset = old.get_model("videomanagement", "MediaAsset")
        prompt = Prompt.objects.create(prompt="Legacy project")
        video = Video.objects.create(
            title="Legacy", prompt=prompt, created_by_id=owner.pk, status="READY"
        )
        scene = Scene.objects.create(video=video, text="Scene", position=1)
        library = Asset.objects.create(
            created_by_id=owner.pk,
            title="Keep my name",
            tags=["favorite"],
            kind="IMAGE",
            file=self.image("blue"),
        )
        shared = Visual.objects.create(scene=scene, file=self.image("blue"))
        image = Visual.objects.create(scene=scene, file=self.image("red"))
        Asset.objects.create(
            created_by_id=owner.pk,
            title="Shared original path",
            kind="IMAGE",
            file=image.file.name,
        )
        clip = Visual.objects.create(
            scene=scene, file=ContentFile(b"legacy clip", name="clip.mp4")
        )
        missing = Visual.objects.create(scene=scene, file="missing.png")
        video.reference_image.save("reference.png", self.image("green"))
        video.cover.save("cover.png", self.image("yellow"))
        other_video = Video.objects.create(
            title="Other", prompt=prompt, created_by_id=other_owner.pk, status="READY"
        )
        other_scene = Scene.objects.create(video=other_video, text="Other", position=1)
        other = Visual.objects.create(scene=other_scene, file=self.image("blue"))
        paths = {row.pk: row.file.name for row in (shared, image, clip, missing, other)}
        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_to)
        new = executor.loader.project_state(self.migrate_to).apps
        Asset = new.get_model("videomanagement", "MediaAsset")
        Visual = new.get_model("videomanagement", "SceneImage")
        self.assertEqual(Asset.objects.count(), 6)
        self.assertEqual(Visual.objects.get(pk=shared.pk).asset_id, library.pk)
        self.assertNotEqual(Visual.objects.get(pk=other.pk).asset_id, library.pk)
        self.assertIsNone(Visual.objects.get(pk=missing.pk).asset_id)
        existing = Asset.objects.get(pk=library.pk)
        self.assertEqual(existing.title, "Keep my name")
        self.assertEqual(existing.tags, ["favorite"])
        for row in Visual.objects.all():
            self.assertEqual(row.file.name, paths[row.pk])
            if row.pk == missing.pk:
                continue
            asset = Asset.objects.get(pk=row.asset_id)
            self.assertNotEqual(asset.file.name, row.file.name)
            self.assertTrue(asset.file.storage.exists(asset.file.name))
        self.assertEqual(
            Asset.objects.get(pk=Visual.objects.get(pk=clip.pk).asset_id).kind, "VIDEO"
        )
        saved_names = set(Asset.objects.values_list("file", flat=True))
        # Simulate retrying an interrupted/non-atomic data migration.
        migration = import_module(
            "apps.videomanagement.migrations.0039_backfill_visual_assets"
        )
        with connection.schema_editor() as editor:
            migration.backfill_visual_assets(new, editor)
        self.assertEqual(set(Asset.objects.values_list("file", flat=True)), saved_names)
        original = Visual.objects.get(pk=image.pk)
        asset = Asset.objects.get(pk=original.asset_id)
        original.file.storage.delete(original.file.name)
        self.assertTrue(asset.file.storage.exists(asset.file.name))


class VisualAssetCommitTests(TransactionTestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        override = override_settings(MEDIA_ROOT=directory.name)
        override.enable()
        self.addCleanup(override.disable)
        self.owner = user.make()
        self.video = video.make(created_by=self.owner, status="READY")

    def image(self, color):
        data = BytesIO()
        Image.new("RGB", (16, 16), color).save(data, format="PNG")
        return ContentFile(data.getvalue(), name=f"{color}.png")

    def test_versions_saved_inside_one_transaction_are_both_archived(self):
        scene = Scene.objects.create(video=self.video, text="Two versions")
        with transaction.atomic():
            visual = SceneImage.objects.create(scene=scene, file=self.image("blue"))
            visual.file = self.image("red")
            visual.save()
        self.assertEqual(MediaAsset.objects.count(), 2)
        self.assertEqual(visual.asset.file.read(), self.image("red").read())
        self.assertTrue(
            all(
                asset.file.storage.exists(asset.file.name)
                for asset in MediaAsset.objects.all()
            )
        )

    def test_failed_queue_does_not_archive_a_reference_in_autocommit(self):
        with patch(
            "apps.videomanagement.tasks.generate_video_task.delay",
            side_effect=ConnectionError("offline"),
        ):
            with self.assertRaises(GenerationQueueUnavailable):
                queue_video_generation(
                    created_by=self.owner,
                    message="A test",
                    reference_image=self.image("blue"),
                )
        self.assertEqual(MediaAsset.objects.count(), 0)
        self.assertFalse(any(path.is_file() for path in self.root.rglob("*")))
