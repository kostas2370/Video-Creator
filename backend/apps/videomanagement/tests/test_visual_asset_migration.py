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
from apps.videomanagement.models import (
    MediaAsset,
    Scene,
    SceneImage,
    Video,
    VideoStatus,
)
from apps.videomanagement.services.videos.jobs import queue_video_generation


class VisualAssetMigrationTests(TransactionTestCase):
    migrate_from = [("videomanagement", "0037_video_is_favorite")]
    migrate_to = [("videomanagement", "0040_sceneimage_asset_owns_file")]

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
        files_before = {
            path.relative_to(directory.name)
            for path in Path(directory.name).rglob("*")
            if path.is_file()
        }
        executor = MigrationExecutor(connection)
        backfill = [("videomanagement", "0039_backfill_visual_assets")]
        executor.migrate(backfill)
        state = executor.loader.project_state(backfill).apps
        migration = import_module(
            "apps.videomanagement.migrations.0039_backfill_visual_assets"
        )
        count = state.get_model("videomanagement", "MediaAsset").objects.count()
        with connection.schema_editor() as editor:
            migration.backfill_visual_assets(state, editor)
        self.assertEqual(
            state.get_model("videomanagement", "MediaAsset").objects.count(), count
        )
        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_to)
        new = executor.loader.project_state(self.migrate_to).apps
        Asset = new.get_model("videomanagement", "MediaAsset")
        Visual = new.get_model("videomanagement", "SceneImage")
        self.assertEqual(Asset.objects.count(), 6)
        self.assertNotEqual(Visual.objects.get(pk=shared.pk).asset_id, library.pk)
        self.assertNotEqual(Visual.objects.get(pk=other.pk).asset_id, library.pk)
        self.assertIsNotNone(Visual.objects.get(pk=missing.pk).asset_id)
        existing = Asset.objects.get(pk=library.pk)
        self.assertEqual(existing.title, "Keep my name")
        self.assertEqual(existing.tags, ["favorite"])
        for row in Visual.objects.all():
            asset = Asset.objects.get(pk=row.asset_id)
            self.assertEqual(asset.file.name, paths[row.pk])
            if row.pk == missing.pk:
                continue
            self.assertTrue(asset.file.storage.exists(asset.file.name))
        self.assertEqual(
            Asset.objects.get(pk=Visual.objects.get(pk=clip.pk).asset_id).kind, "VIDEO"
        )
        self.assertEqual(
            {
                path.relative_to(directory.name)
                for path in Path(directory.name).rglob("*")
                if path.is_file()
            },
            files_before,
        )
        self.assertNotIn("file", {field.name for field in Visual._meta.fields})
        # Reversing the column removal restores each scene's original file path.
        executor = MigrationExecutor(connection)
        executor.migrate(backfill)
        restored = executor.loader.project_state(backfill).apps.get_model(
            "videomanagement", "SceneImage"
        )
        self.assertEqual(
            {row.pk: row.file.name for row in restored.objects.all()}, paths
        )
        MigrationExecutor(connection).migrate(self.migrate_to)
        Video = new.get_model("videomanagement", "Video")
        Video.objects.filter(pk=video.pk).delete()
        for asset in Asset.objects.exclude(file="missing.png"):
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

    @patch("apps.videomanagement.models.send_email.delay")
    def test_failed_queue_removes_uploaded_reference_in_autocommit(self, send_email):
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
        failed = Video.objects.exclude(pk=self.video.pk).get()
        self.assertEqual(failed.status, VideoStatus.FAILED)
        self.assertFalse(failed.reference_image)
        send_email.assert_called_once()
        self.assertEqual(MediaAsset.objects.count(), 0)
        self.assertFalse(any(path.is_file() for path in self.root.rglob("*")))

    def test_generated_file_is_registered_without_writing_another_copy(self):
        source = self.root / "generated.png"
        source.write_bytes(self.image("blue").read())
        scene = Scene.objects.create(video=self.video, text="Generated")
        visual = SceneImage.objects.create(scene=scene, file="generated.png")
        self.assertEqual(visual.asset.file.name, "generated.png")
        self.assertEqual(list(self.root.rglob("*.png")), [source])
        scene.delete()
        self.assertTrue(source.exists())
        self.assertTrue(MediaAsset.objects.filter(pk=visual.asset_id).exists())

    def test_failed_scene_edit_does_not_remove_a_reused_asset(self):
        scene = Scene.objects.create(video=self.video, text="Original")
        visual = SceneImage.objects.create(scene=scene, file=self.image("blue"))
        asset = visual.asset
        source = Path(asset.file.path)
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                visual.file = self.image("blue")
                visual.save()
                raise RuntimeError("Edit rolled back")
        visual.discard_upload()
        self.assertTrue(source.exists())
        self.assertEqual(MediaAsset.objects.count(), 1)
        self.assertEqual(visual.asset_id, asset.pk)

    def test_deleting_a_legacy_duplicate_keeps_the_file_used_by_another_asset(self):
        scene = Scene.objects.create(video=self.video, text="Shared legacy path")
        visual = SceneImage.objects.create(scene=scene, file=self.image("blue"))
        asset = visual.asset
        duplicate = MediaAsset.objects.create(
            created_by=self.owner,
            title="Legacy duplicate",
            kind="IMAGE",
            file=asset.file.name,
        )
        duplicate.delete()
        self.assertTrue(Path(asset.file.path).exists())
        scene.delete()
        asset.delete()
        self.assertFalse(Path(asset.file.path).exists())

    def test_account_deletion_can_delete_scenes_and_their_assets_together(self):
        scene = Scene.objects.create(video=self.video, text="Account scene")
        visual = SceneImage.objects.create(scene=scene, file=self.image("blue"))
        source = Path(visual.file.path)
        self.owner.delete()
        self.assertFalse(SceneImage.objects.filter(pk=visual.pk).exists())
        self.assertFalse(MediaAsset.objects.filter(pk=visual.asset_id).exists())
        self.assertFalse(source.exists())
