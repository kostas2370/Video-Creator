import tempfile
import wave
from pathlib import Path
from unittest.mock import patch

from django.test import override_settings
from django.urls import reverse
from PIL import Image

from apps.usermanagement.baker_recipes import user
from apps.videomanagement.baker_recipes import scene, scene_image
from apps.videomanagement.models import VideoStatus
from .base import ApiTestCase


class SceneShotTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.enterContext(override_settings(MEDIA_ROOT=directory.name))
        Image.new("RGB", (32, 32), "red").save(self.root / "red.png")
        with wave.open(str(self.root / "voice.wav"), "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(8000)
            audio.writeframes(b"\0\0" * 32000)
        self.video = self.video_for(
            status=VideoStatus.READY,
            settings={
                "narration": True,
                "subtitles": True,
                "transition_default": "CUT",
            },
        )
        self.scene = scene.make(
            video=self.video,
            file="voice.wav",
            text="One two three four.",
            is_last=False,
            pause_after=0.5,
        )
        self.first = scene_image.make(
            scene=self.scene,
            file="red.png",
            position=0,
            timing_weight=1,
            with_audio=False,
        )
        self.second = scene_image.make(
            scene=self.scene,
            file="red.png",
            position=1,
            timing_weight=3,
            with_audio=False,
        )
        self.url = reverse("scene-shots", args=[self.scene.pk])

    def save(self, shots, expected=None):
        return self.client.patch(
            self.url,
            {
                "shots": shots,
                "expected_ids": expected or [str(self.first.pk), str(self.second.pk)],
            },
            format="json",
        )

    def test_reorders_shots_without_changing_narration_and_removes_only_the_selected_placement(
        self,
    ):
        response = self.save(
            [
                {"id": str(self.second.pk), "timing_weight": 2},
                {"id": str(self.first.pk), "timing_weight": 1},
            ]
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            [row["id"] for row in response.data["shots"]],
            [str(self.second.pk), str(self.first.pk)],
        )
        self.assertEqual(response.data["file"], self.scene.file.url)
        response = self.save(
            [{"id": str(self.second.pk)}],
            expected=[str(self.second.pk), str(self.first.pk)],
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(
            self.first.asset.file.storage.exists(self.first.asset.file.name)
        )
        self.assertEqual(self.scene.scene_images.count(), 1)

    def test_preview_has_one_narration_track_and_proportional_shots_with_a_final_pause(
        self,
    ):
        response = self.client.get(reverse("video-preview", args=[self.video.pk]))
        self.assertEqual(response.status_code, 200, response.data)
        segment = response.data["segments"][0]
        self.assertEqual(segment["duration"], 4.5)
        self.assertEqual(
            [(s["start"], s["duration"]) for s in segment["shots"]], [(0, 1), (1, 3.5)]
        )
        self.assertEqual(len(response.data["audio_tracks"]), 1)
        self.assertTrue(response.data["captions"])

    def test_rejects_foreign_duplicate_empty_stale_and_invalid_timing_edits(self):
        foreign_video = self.video_for(owner=user.make(), status="READY")
        foreign = scene_image.make(
            scene=scene.make(video=foreign_video), file="red.png"
        )
        for shots in (
            [],
            [{"id": str(foreign.pk)}],
            [{"id": str(self.first.pk)}] * 2,
            [{"id": str(self.first.pk), "timing_weight": 0}],
            [{"id": str(self.first.pk), "trim_start": 1}],
            [{"id": str(self.first.pk), "timing_weight": "NaN"}],
        ):
            self.assertEqual(self.save(shots).status_code, 400)
        self.assertEqual(
            self.save(
                [{"id": str(self.first.pk)}], expected=[str(self.first.pk)]
            ).status_code,
            409,
        )
        self.video.status = "RENDERING"
        self.video.save()
        self.assertEqual(self.save([{"id": str(self.first.pk)}]).status_code, 409)
        self.client.force_authenticate(foreign_video.created_by)
        self.assertEqual(self.save([{"id": str(self.first.pk)}]).status_code, 403)

    def test_upload_and_library_replacement_target_only_the_chosen_shot(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from apps.videomanagement.models import MediaAsset

        url = reverse("scene-change-image-scene", args=[self.scene.pk])
        upload = SimpleUploadedFile(
            "new.png", (self.root / "red.png").read_bytes(), content_type="image/png"
        )
        response = self.client.post(url, {"image": upload}, format="multipart")
        self.assertEqual(response.status_code, 200, response.data)
        appended = self.scene.scene_images.last()
        self.assertEqual(appended.position, 2)
        self.assertEqual(self.scene.scene_images.count(), 3)
        asset = MediaAsset.objects.create(
            created_by=self.user, kind="IMAGE", file="red.png"
        )
        response = self.client.post(
            reverse("mediaasset-use", args=[asset.pk]),
            {
                "video_id": str(self.video.pk),
                "scene_id": str(self.scene.pk),
                "purpose": "visual",
                "scene_image": str(appended.pk),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        appended.refresh_from_db()
        self.assertEqual(appended.asset_id, asset.pk)
        self.assertEqual(self.scene.scene_images.count(), 3)
        self.first.refresh_from_db()
        self.assertNotEqual(self.first.asset_id, asset.pk)

    def test_manual_scene_keeps_its_length_when_a_second_shot_is_added(self):
        from apps.videomanagement.services.scenes.shots import next_shot_position
        from apps.videomanagement.utils.timing import scene_timing

        self.second.delete()
        self.video.settings = {"narration": False}
        self.video.save()
        before = scene_timing(self.scene, self.first)
        position = next_shot_position(self.scene)
        scene_image.make(scene=self.scene, file="red.png", position=position)
        self.assertEqual(scene_timing(self.scene, self.first), before)

    def test_generation_targets_one_shot_and_can_append_without_replacing(self):
        url = reverse("scene-generate-image-scene", args=[self.scene.pk])
        with patch("apps.videomanagement.tasks.scenes.generate_new_image") as generate:
            response = self.client.post(
                url,
                {"image_description": "A blue cup", "scene_image": str(self.second.pk)},
                format="json",
            )
            self.assertEqual(response.status_code, 202, response.data)
            self.run_scene_job()
            self.assertEqual(generate.call_args.args[0].pk, self.second.pk)
            response = self.client.post(
                url, {"image_description": "A new cup", "new_shot": True}, format="json"
            )
            self.assertEqual(response.status_code, 202, response.data)
            self.run_scene_job()
            self.assertTrue(generate.call_args.args[0]._state.adding)
            self.assertEqual(generate.call_args.args[0].position, 2)
            self.assertEqual(self.scene.scene_images.count(), 2)
