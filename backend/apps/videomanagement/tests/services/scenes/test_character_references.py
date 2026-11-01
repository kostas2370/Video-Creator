import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from django.test import TestCase, override_settings
from rest_framework.exceptions import ValidationError

from apps.videomanagement.baker_recipes import scene, scene_image, video
from apps.videomanagement.services.scenes import visuals
from apps.videomanagement.services.scenes.starting_images import (
    animate_starting_image,
    save_starting_image,
    starting_image_status,
)


class CharacterShotReferenceTests(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        storage = override_settings(MEDIA_ROOT=self.tmp.name)
        storage.enable()
        self.addCleanup(storage.disable)
        self.frame = str(Path(self.tmp.name, "starting.png"))
        Path(self.frame).write_bytes(b"starting image")
        Path(self.tmp.name, "cast.png").write_bytes(b"cast")
        self.video = video.make(
            mode="AI",
            status="READY",
            reference_image="cast.png",
            settings={
                "provider": "kling",
                "character_references": True,
                "video_format": "PORTRAIT",
                "narration": False,
            },
        )
        self.scene = scene.make(video=self.video, text="Milo finds a lantern")
        self.provider = Mock(return_value="images/shot.mp4")
        resolver = patch.object(
            visuals.ImageProviderRegistry, "resolve", return_value=self.provider
        )
        resolver.start()
        self.addCleanup(resolver.stop)
        generator = patch.object(
            visuals.openai_images, "generate_openai_image", return_value=self.frame
        )
        self.starting = generator.start()
        self.addCleanup(generator.stop)

    def prepare(self):
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
        self.scene.refresh_from_db()

    def approve(self):
        save_starting_image(
            self.scene, operation="approve", asset_id=self.scene.starting_asset_id
        )
        self.scene.refresh_from_db()

    def test_generation_prepares_a_scene_image_without_animating(self):
        self.prepare()
        self.assertEqual(
            self.starting.call_args.kwargs["reference"], self.video.reference_image.path
        )
        self.assertEqual(self.starting.call_args.kwargs["reference_role"], "character")
        self.assertIn("Milo at the forest gate", self.starting.call_args.args[0])
        self.assertTrue(Path(self.scene.starting_asset.file.path).exists())
        self.assertEqual(starting_image_status(self.scene), "needs_review")
        self.provider.assert_not_called()
        self.assertFalse(self.scene.scene_images.first().file)

    def test_animation_requires_approval_and_uses_the_exact_saved_image(self):
        self.prepare()
        with self.assertRaises(ValidationError):
            animate_starting_image(self.scene, self.scene.starting_asset_id)
        self.provider.assert_not_called()
        self.approve()
        animate_starting_image(self.scene, self.scene.starting_asset_id)
        self.assertEqual(
            self.provider.call_args.kwargs["reference"],
            self.scene.starting_asset.file.path,
        )
        self.starting.assert_called_once()
        self.assertEqual(self.scene.scene_images.first().file.name, "images/shot.mp4")

    def test_replacement_image_preserves_existing_video_and_requires_new_approval(self):
        target = scene_image.make(
            scene=self.scene, file="images/approved.mp4", prompt="Old shot"
        )
        self.prepare()
        self.approve()
        target.prompt = "Milo inside the workshop"
        visuals.generate_new_image(target, self.video)
        target.refresh_from_db()
        self.scene.refresh_from_db()
        self.assertEqual(target.file.name, "images/approved.mp4")
        self.assertEqual(target.prompt, "Old shot")
        self.assertEqual(
            self.scene.starting_image_context["description"], "Milo inside the workshop"
        )
        self.assertEqual(starting_image_status(self.scene), "needs_review")
        self.provider.assert_not_called()

    def test_image_failure_preserves_saved_image_and_video(self):
        self.prepare()
        self.approve()
        asset_id = self.scene.starting_asset_id
        target = self.scene.scene_images.first()
        target.file = "images/approved.mp4"
        target.save()
        self.starting.side_effect = RuntimeError("provider unavailable")
        with self.assertRaises(RuntimeError):
            visuals.generate_new_image(target, self.video)
        target.refresh_from_db()
        self.scene.refresh_from_db()
        self.assertEqual(target.file.name, "images/approved.mp4")
        self.assertEqual(self.scene.starting_asset_id, asset_id)
        self.assertEqual(starting_image_status(self.scene), "approved")
        self.provider.assert_not_called()

    def test_failed_animation_can_retry_without_regenerating_the_image(self):
        self.prepare()
        self.approve()
        target = self.scene.scene_images.first()
        target.file = "images/approved.mp4"
        target.save()
        self.provider.side_effect = RuntimeError("video unavailable")
        with self.assertRaises(RuntimeError):
            animate_starting_image(self.scene, self.scene.starting_asset_id)
        target.refresh_from_db()
        self.assertEqual(target.file.name, "images/approved.mp4")
        self.provider.side_effect = None
        animate_starting_image(self.scene, self.scene.starting_asset_id)
        self.starting.assert_called_once()
        target.refresh_from_db()
        self.assertEqual(target.file.name, "images/shot.mp4")

    def test_resume_reuses_pending_images_and_never_starts_animation(self):
        self.prepare()
        self.approve()
        self.prepare()
        self.assertEqual(self.scene.scene_images.count(), 1)
        self.starting.assert_called_once()
        self.provider.assert_not_called()

    def test_changed_shot_plan_invalidates_approval_without_paid_requests(self):
        self.prepare()
        self.approve()
        self.scene.shot_plan = {"shot_size": "CLOSE_UP"}
        self.scene.save(update_fields=["shot_plan"])
        with self.assertRaises(ValidationError):
            animate_starting_image(self.scene, self.scene.starting_asset_id)
        self.provider.assert_not_called()

    def test_stale_image_cannot_be_approved_or_animated(self):
        self.prepare()
        from uuid import uuid4

        with self.assertRaises(ValidationError):
            save_starting_image(self.scene, operation="approve", asset_id=uuid4())
        self.approve()
        with self.assertRaises(ValidationError):
            animate_starting_image(self.scene, uuid4())
        self.provider.assert_not_called()

    def test_missing_cast_sheet_never_falls_back_to_unreferenced_generation(self):
        Path(self.video.reference_image.path).unlink()
        with self.assertRaisesMessage(ValueError, "character reference is missing"):
            visuals.character_starting_frame(
                self.video, "Milo", "", "kling", "AI", self.video.created_by
            )
        self.starting.assert_not_called()

    def test_changed_style_is_used_when_regenerating_the_starting_image(self):
        self.prepare()
        self.approve()
        self.video.settings["style"] = "cinematic"
        self.video.save(update_fields=["settings"])
        target = self.scene.scene_images.first()
        target.scene = self.scene
        self.scene.video = self.video
        self.assertEqual(starting_image_status(self.scene), "needs_review")
        visuals.generate_new_image(target, self.video)
        self.assertEqual(self.starting.call_args.kwargs["style"], "cinematic")
        self.provider.assert_not_called()

    def test_automatic_preparation_failure_does_not_clear_an_existing_clip(self):
        target = scene_image.make(scene=self.scene, file="images/approved.mp4")
        self.starting.side_effect = RuntimeError("provider unavailable")
        self.prepare()
        target.refresh_from_db()
        self.assertEqual(target.file.name, "images/approved.mp4")
        self.provider.assert_not_called()
