import tempfile
from pathlib import Path
from django.test import override_settings

from unittest.mock import Mock, patch

from django.test import TestCase

from apps.videomanagement.baker_recipes import scene, scene_image, video
from apps.videomanagement.services.scenes import visuals


class CharacterShotReferenceTests(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        storage = override_settings(MEDIA_ROOT=self.tmp.name)
        storage.enable()
        self.addCleanup(storage.disable)
        self.frame = str(Path(self.tmp.name, "starting.png"))
        Path(self.frame).write_bytes(b"starting image")
        self.video = video.make(
            mode="AI",
            reference_image="media/cast.png",
            settings={
                "provider": "kling",
                "character_references": True,
                "video_format": "PORTRAIT",
                "narration": False,
            },
        )
        self.scene = scene.make(video=self.video, text="Milo finds a lantern")

    def test_video_generation_animates_a_scene_image_rather_than_the_cast_sheet(self):
        provider = Mock(return_value="images/shot.mp4")
        with (
            patch.object(
                visuals.ImageProviderRegistry, "resolve", return_value=provider
            ),
            patch.object(visuals, "stored_file_exists", return_value=True),
            patch.object(
                visuals.openai_images,
                "generate_openai_image",
                return_value=self.frame,
            ) as starting,
        ):
            visuals.create_image_scene(
                self.video,
                "Milo at the forest gate",
                self.scene.text,
                self.video.dir_name,
                scene=self.scene,
                mode="AI",
                provider="kling",
                user=self.video.created_by,
            )
        self.assertEqual(
            starting.call_args.kwargs["reference"], self.video.reference_image.path
        )
        self.assertEqual(starting.call_args.kwargs["reference_role"], "character")
        self.assertIn("Milo at the forest gate", starting.call_args.args[0])
        self.scene.refresh_from_db()
        self.assertEqual(provider.call_args.kwargs["reference"], self.scene.starting_asset.file.path)

    def test_replacing_a_video_shot_uses_the_episode_cast_again(self):
        target = scene_image.make(
            scene=self.scene, prompt="Milo inside the workshop", file="images/old.mp4"
        )
        provider = Mock(return_value="images/new.mp4")
        with (
            patch.object(
                visuals.ImageProviderRegistry, "resolve", return_value=provider
            ),
            patch.object(visuals, "stored_file_exists", return_value=True),
            patch.object(
                visuals.openai_images,
                "generate_openai_image",
                return_value=self.frame,
            ) as starting,
        ):
            visuals.generate_new_image(target, self.video)
        self.assertEqual(
            starting.call_args.kwargs["reference"], self.video.reference_image.path
        )
        self.scene.refresh_from_db()
        self.assertEqual(provider.call_args.kwargs["reference"], self.scene.starting_asset.file.path)

    def test_starting_image_failure_preserves_the_saved_video_shot(self):
        target = scene_image.make(
            scene=self.scene, prompt="Milo at the gate", file="images/approved.mp4"
        )
        provider = Mock()
        with (
            patch.object(
                visuals.ImageProviderRegistry, "resolve", return_value=provider
            ),
            patch.object(visuals, "stored_file_exists", return_value=True),
            patch.object(
                visuals.openai_images,
                "generate_openai_image",
                side_effect=RuntimeError("provider unavailable"),
            ),
        ):
            with self.assertRaises(RuntimeError):
                visuals.generate_new_image(target, self.video)
        target.refresh_from_db()
        self.assertEqual(target.file.name, "images/approved.mp4")
        provider.assert_not_called()

    def test_missing_cast_sheet_never_falls_back_to_unreferenced_generation(self):
        with (
            patch.object(visuals, "stored_file_exists", return_value=False),
            patch.object(visuals.openai_images, "generate_openai_image") as image,
        ):
            with self.assertRaisesMessage(ValueError, "character reference is missing"):
                visuals.character_starting_frame(
                    self.video, "Milo", "", "kling", "AI", self.video.created_by
                )
        image.assert_not_called()

    def test_failed_video_keeps_image_and_retry_does_not_regenerate_it(self):
        provider = Mock(side_effect=RuntimeError("video unavailable"))
        with (
            patch.object(visuals.ImageProviderRegistry, "resolve", return_value=provider),
            patch.object(visuals, "stored_file_exists", return_value=True),
            patch.object(visuals.openai_images, "generate_openai_image", return_value=self.frame) as starting,
        ):
            visuals.create_image_scene(
                self.video, "Milo at gate", self.scene.text, self.video.dir_name,
                mode="AI", provider="kling", user=self.video.created_by, scene=self.scene,
            )
            self.scene.refresh_from_db()
            self.assertTrue(self.scene.starting_asset_id)
            self.assertTrue(Path(self.scene.starting_asset.file.path).exists())
            target = self.scene.scene_images.first()
            self.assertFalse(target.file)
            provider.side_effect = None
            provider.return_value = "images/retried.mp4"
            visuals.generate_new_image(target, self.video)
            starting.assert_called_once()
            self.assertEqual(provider.call_args.kwargs["reference"], self.scene.starting_asset.file.path)
            target.refresh_from_db()
            self.assertEqual(target.file.name, "images/retried.mp4")

    def test_changed_shot_does_not_reuse_an_outdated_starting_image(self):
        provider = Mock(return_value="images/shot.mp4")
        with (
            patch.object(visuals.ImageProviderRegistry, "resolve", return_value=provider),
            patch.object(visuals, "stored_file_exists", return_value=True),
            patch.object(visuals.openai_images, "generate_openai_image", return_value=self.frame) as starting,
        ):
            visuals.create_image_scene(
                self.video, "Milo at gate", self.scene.text, self.video.dir_name,
                mode="AI", provider="kling", user=self.video.created_by, scene=self.scene,
            )
            target = self.scene.scene_images.first()
            target.prompt = "Milo on the moon"
            visuals.generate_new_image(target, self.video)
            self.assertEqual(starting.call_count, 2)

    def test_carry_on_updates_the_failed_row_instead_of_hiding_the_new_clip(self):
        provider = Mock(side_effect=RuntimeError("video unavailable"))
        with (
            patch.object(visuals.ImageProviderRegistry, "resolve", return_value=provider),
            patch.object(visuals, "stored_file_exists", return_value=True),
            patch.object(visuals.openai_images, "generate_openai_image", return_value=self.frame) as starting,
        ):
            def attempt():
                visuals.create_image_scene(
                    self.video, "Milo at gate", self.scene.text, self.video.dir_name,
                    mode="AI", provider="kling", user=self.video.created_by, scene=self.scene,
                )
            attempt()
            self.scene.refresh_from_db()
            provider.side_effect = None
            provider.return_value = "images/recovered.mp4"
            attempt()
            starting.assert_called_once()
            self.assertEqual(self.scene.scene_images.count(), 1)
            self.assertEqual(self.scene.scene_images.first().file.name, "images/recovered.mp4")
