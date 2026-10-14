import io
import subprocess
import tempfile
import wave
from pathlib import Path
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from PIL import Image

from ...models import Video, VideoStatus, VideoType
from ...utils.composer.render import make_video
from ...utils.timing import media_timing
from .base import ApiTestCase
from apps.usermanagement.baker_recipes import user


class ManualVideoTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        settings = override_settings(MEDIA_ROOT=self.directory.name)
        settings.enable()
        self.addCleanup(settings.disable)
        self.user.generation_limit_for_ai = 0
        self.user.save()

    def create_project(self, **choices):
        response = self.client.post(reverse("video-manual"), {"title": "My own video", **choices}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return Video.objects.get(pk=response.data["id"])

    def photo(self):
        data = io.BytesIO()
        Image.new("RGB", (32, 18), "blue").save(data, "PNG")
        return SimpleUploadedFile("photo.png", data.getvalue(), content_type="image/png")

    def audio(self):
        path = Path(self.directory.name, "upload.wav")
        with wave.open(str(path), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(8000)
            output.writeframes(b"\x10\x00" * 16000)
        return SimpleUploadedFile("my-song.wav", path.read_bytes(), content_type="audio/wav")

    def add_scene(self, video, **choices):
        response = self.client.post(reverse("video-add-scene", args=[video.pk]), choices, format="multipart")
        self.assertEqual(response.status_code, 201, response.data)
        return response

    def test_empty_project_is_ready_and_listed_without_ai_keys_or_credits(self):
        with patch("apps.videomanagement.views.video_view.generate_video_task.delay") as generation:
            video = self.create_project(video_format="PORTRAIT")
        generation.assert_not_called()
        self.assertEqual(video.status, VideoStatus.READY)
        self.assertEqual(video.video_type, VideoType.MANUAL)
        self.assertIsNone(video.voice_model)
        self.assertIsNone(video.gpt_answer)
        self.assertFalse(video.settings["narration"])
        self.assertEqual(video.settings["video_format"], "PORTRAIT")
        self.assertEqual(video.scenes.count(), 0)
        response = self.client.get(reverse("video-list"))
        self.assertIn(str(video.pk), [str(row["id"]) for row in response.data["results"]])
        with patch("apps.videomanagement.views.video_view.render_video_task.delay") as render:
            self.assertEqual(self.client.patch(reverse("video-render-video", args=[video.pk])).status_code, 400)
        render.assert_not_called()

    def test_upload_insert_edit_caption_duration_and_export_without_generation(self):
        video = self.create_project()
        with patch("apps.videomanagement.views.video_view.create_scene_task.delay") as generation:
            self.add_scene(video, image=self.photo(), text="My own caption", duration=2)
            self.add_scene(video, image=self.photo(), position=1, duration=1)
        generation.assert_not_called()
        scenes = list(video.scenes.all())
        self.assertEqual([scene.position for scene in scenes], [1, 2])
        self.assertEqual(scenes[1].text, "My own caption")
        self.assertTrue(Path(scenes[0].scene_images.first().file.path).exists())
        with patch("apps.videomanagement.views.scene_view.queue_scene_job") as job:
            response = self.client.patch(reverse("scene-detail", args=[scenes[1].pk]), {"text": "Updated caption"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        job.assert_not_called()
        self.assertEqual(self.client.patch(reverse("scene-timing", args=[scenes[1].pk]), {"duration": 1.5}, format="json").status_code, 200)
        response = self.client.get(reverse("video-preview", args=[video.pk]))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertAlmostEqual(response.data["duration"], 2.5)
        response = self.client.get(reverse("video-subtitles", args=[video.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertIn("Updated caption", response.content.decode())
        with patch("apps.videomanagement.utils.composer.render.output_size", return_value=(32, 18)):
            result = make_video(video)
        self.assertEqual(result.status, VideoStatus.COMPLETED)
        self.assertAlmostEqual(media_timing(result.output.path)["duration"], 2.5, delta=0.1)
        self.user.refresh_from_db()
        self.assertEqual(self.user.generation_limit_for_ai, 0)

    def test_uploaded_video_keeps_audio_and_uses_clip_length(self):
        video = self.create_project()
        path = Path(self.directory.name, "clip.webm")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=red:s=32x18:d=2",
                        "-f", "lavfi", "-i", "sine=frequency=440:duration=2", "-c:v", "libvpx", "-c:a", "libopus", str(path)],
                       capture_output=True, check=True, timeout=30)
        response = self.add_scene(video, image=SimpleUploadedFile("clip.webm", path.read_bytes(), content_type="video/webm"))
        self.assertTrue(response.data["scenes"][0]["scene_image"]["with_audio"])
        self.assertAlmostEqual(response.data["scenes"][0]["timing"]["duration"], 2, delta=0.05)
        scene = video.scenes.first()
        self.assertEqual(self.client.patch(reverse("scene-timing", args=[scene.pk]), {"duration": 1}, format="json").status_code, 200)
        with patch("apps.videomanagement.utils.composer.render.output_size", return_value=(32, 18)):
            result = make_video(video)
        self.assertAlmostEqual(media_timing(result.output.path)["duration"], 1, delta=0.05)

    def test_photos_default_to_five_seconds_and_blank_scenes_support_captions(self):
        video = self.create_project()
        response = self.add_scene(video, image=self.photo())
        self.assertEqual(response.data["scenes"][0]["timing"]["duration"], 5)
        self.add_scene(video, text="A title card", duration=3)
        response = self.client.get(reverse("video-preview", args=[video.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["duration"], 8)
        self.assertEqual(self.client.get(reverse("video-subtitles", args=[video.pk])).status_code, 200)

    def test_recorded_voice_and_uploaded_music_need_no_credits(self):
        video = self.create_project()
        self.add_scene(video, image=self.photo())
        scene = video.scenes.first()
        response = self.client.post(reverse("scene-voiceover", args=[scene.pk]), {"file": self.audio()}, format="multipart")
        self.assertEqual(response.status_code, 200)
        response = self.client.post(reverse("video-music", args=[video.pk]), {"file": self.audio()}, format="multipart")
        self.assertEqual(response.status_code, 200, response.data)
        video.refresh_from_db()
        old_music = video.music_id
        self.assertTrue(video.music_id)
        response = self.client.get(reverse("video-preview", args=[video.pk]))
        self.assertEqual(len(response.data["audio_tracks"]), 1)
        self.assertEqual(self.client.delete(reverse("video-music", args=[video.pk])).status_code, 200)
        video.refresh_from_db()
        self.assertIsNone(video.music_id)
        from ...models import Music
        self.assertFalse(Music.objects.filter(pk=old_music).exists())

    def test_manual_actions_check_ownership_and_editing_locks(self):
        video = self.create_project()
        self.add_scene(video, text="A scene")
        other = user.make()
        self.client.force_authenticate(other)
        for name in ("video-add-scene", "video-music"):
            self.assertIn(self.client.post(reverse(name, args=[video.pk]), {}).status_code, (403, 404))
        scene = video.scenes.first()
        self.assertIn(self.client.patch(reverse("scene-detail", args=[scene.pk]), {"text": "Changed"}).status_code, (403, 404))
        self.client.force_authenticate(self.user)
        video.status = VideoStatus.RENDERING
        video.save()
        self.assertEqual(self.client.post(reverse("video-add-scene", args=[video.pk]), {}).status_code, 409)
        self.assertEqual(self.client.patch(reverse("scene-detail", args=[scene.pk]), {"text": "Changed"}).status_code, 409)

    def test_rejects_invalid_media_and_nonfinite_durations_without_adding_scenes(self):
        video = self.create_project()
        for name in ("fake.png", "fake.mp4", "unexpected.txt"):
            response = self.client.post(reverse("video-add-scene", args=[video.pk]), {"image": SimpleUploadedFile(name, b"not media")}, format="multipart")
            self.assertEqual(response.status_code, 400)
        for duration in (0, -1, 901, "NaN", "Infinity"):
            response = self.client.post(reverse("video-add-scene", args=[video.pk]), {"duration": duration}, format="json")
            self.assertEqual(response.status_code, 400)
        self.assertEqual(video.scenes.count(), 0)

    def test_caption_can_be_cleared_without_charging_for_ai(self):
        video = self.create_project()
        self.add_scene(video, text="Old caption")
        scene = video.scenes.first()
        response = self.client.patch(reverse("scene-detail", args=[scene.pk]), {"text": ""}, format="json")
        self.assertEqual(response.status_code, 200)
        scene.refresh_from_db()
        self.assertEqual(scene.text, "")

    def test_media_replacement_reordering_and_deletion_do_not_need_credits(self):
        video = self.create_project()
        self.add_scene(video, text="First")
        self.add_scene(video, text="Second")
        first, second = list(video.scenes.all())
        response = self.client.post(reverse("scene-change-image-scene", args=[first.pk]), {"image": self.photo()}, format="multipart")
        self.assertEqual(response.status_code, 200, response.data)
        response = self.client.post(reverse("video-reorder-scenes", args=[video.pk]), {"scene_ids": [str(second.pk), str(first.pk)]}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(list(video.scenes.values_list("pk", flat=True)), [second.pk, first.pk])
        self.assertEqual(self.client.delete(reverse("scene-detail", args=[first.pk])).status_code, 204)
        self.assertEqual(video.scenes.count(), 1)
        self.user.refresh_from_db()
        self.assertEqual(self.user.generation_limit_for_ai, 0)

    def test_shortened_voice_and_silent_captions_share_the_preview_timing(self):
        video = self.create_project()
        self.add_scene(video, text="Recorded caption", duration=1)
        scene = video.scenes.first()
        self.assertEqual(self.client.post(reverse("scene-voiceover", args=[scene.pk]), {"file": self.audio()}, format="multipart").status_code, 200)
        self.assertEqual(self.client.patch(reverse("scene-audio", args=[scene.pk]), {"crossfade": 0.5}, format="json").status_code, 200)
        self.add_scene(video, text="Silent caption", duration=2)
        response = self.client.get(reverse("video-preview", args=[video.pk]))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["duration"], 3)
        self.assertEqual(response.data["audio_tracks"][0]["duration"], 1)
        self.assertEqual([cue["text"] for cue in response.data["captions"]], ["Recorded caption", "Silent caption"])
        self.assertEqual(response.data["captions"][-1]["end"], 3)

    def test_optional_ai_visual_generation_resolves_a_provider_only_when_requested(self):
        from ...models import SceneImage
        from ...utils.scenes import generate_new_image

        video = self.create_project()
        self.add_scene(video, text="My scene")
        visual = SceneImage.objects.create(scene=video.scenes.first(), prompt="A blue ocean")
        with patch("apps.videomanagement.utils.scenes.ImageProviderRegistry.resolve") as resolve:
            resolve.return_value.return_value = "generated.png"
            generate_new_image(visual, video)
        resolve.assert_called_once_with("AI", "OPENAI")
        self.assertTrue(Path(video.dir_name, "images").exists())

    def test_automatic_duration_follows_recorded_audio_and_override_is_optional_settings(self):
        video = self.create_project()
        self.add_scene(video, image=self.photo())
        scene = video.scenes.first()
        self.assertEqual(scene.audio_settings, {})
        response = self.client.post(reverse("scene-voiceover", args=[scene.pk]), {"file": self.audio()}, format="multipart")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["timing"]["duration"], 2)
        self.assertNotIn("duration", response.data)
        self.assertNotIn("duration", response.data["audio_settings"])
        response = self.client.patch(reverse("scene-timing", args=[scene.pk]), {"duration": 1}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["audio_settings"]["duration"], 1)
        self.assertEqual(response.data["timing"]["duration"], 1)
        response = self.client.patch(reverse("scene-timing", args=[scene.pk]), {"duration": None}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("duration", response.data["audio_settings"])
        self.assertEqual(response.data["timing"]["duration"], 2)
