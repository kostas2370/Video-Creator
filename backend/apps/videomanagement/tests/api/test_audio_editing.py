import tempfile
import wave
from pathlib import Path
from unittest.mock import patch

import numpy as np
from django.test import override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from ...baker_recipes import scene
from ...models import VideoStatus
from ...utils.audio_editing import music_gain, voice_tracks, waveform
from ...utils.composer.audio import scene_audio_segments, compose_edited_audio
from .base import ApiTestCase
from apps.usermanagement.baker_recipes import user


class AudioEditingTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        settings = override_settings(MEDIA_ROOT=self.directory.name)
        settings.enable()
        self.addCleanup(settings.disable)
        self.video = self.video_for(status=VideoStatus.READY, settings={"narration": True})
        self.path = Path(self.directory.name, "voice.wav")
        self.make_audio(self.path)
        self.scene = scene.make(video=self.video, file="voice.wav", is_last=False)

    def make_audio(self, path):
        with wave.open(str(path), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(8000)
            samples = np.zeros(32000)
            samples[8000:24000] = 0.3 * np.sin(np.arange(16000) * 0.2)
            output.writeframes((samples * 32767).astype("<i2").tobytes())

    def url(self, name, obj=None):
        return reverse(name, args=[(obj or self.scene).pk])

    def test_trim_validation_and_timing(self):
        response = self.client.patch(self.url("scene-audio"), {"trim_start": 1, "trim_end": 3, "delay": 0.5}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertAlmostEqual(response.data["timing"]["duration"], 2.5)
        for data in ({"trim_end": 0.5}, {"trim_start": 6}, {"delay": "Infinity"}, {"volume": -1}):
            self.assertEqual(self.client.patch(self.url("scene-audio"), data, format="json").status_code, 400)

    def test_waveform_detects_speech_and_silence(self):
        response = self.client.get(self.url("scene-waveform"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["peaks"]), 600)
        self.assertEqual(response.data["speech"], [[1.0, 3.0]])

    def test_upload_and_restore_preserve_generated_audio(self):
        upload = SimpleUploadedFile("take.wav", self.path.read_bytes(), content_type="audio/wav")
        response = self.client.post(self.url("scene-voiceover"), {"file": upload}, format="multipart")
        self.assertEqual(response.status_code, 200)
        self.scene.refresh_from_db()
        uploaded_path = self.scene.voiceover.path
        self.assertTrue(Path(uploaded_path).exists())
        self.assertEqual(self.scene.file.name, "voice.wav")
        self.assertEqual(self.client.delete(self.url("scene-voiceover")).status_code, 200)
        self.scene.refresh_from_db()
        self.assertFalse(self.scene.voiceover)
        self.assertTrue(self.path.exists())

    def test_rejects_fake_audio_and_edits_while_rendering(self):
        response = self.client.post(self.url("scene-voiceover"), {"file": SimpleUploadedFile("fake.wav", b"not audio")}, format="multipart")
        self.assertEqual(response.status_code, 400)
        self.video.status = VideoStatus.RENDERING
        self.video.save()
        self.assertEqual(self.client.patch(self.url("scene-audio"), {"fade_in": 1}, format="json").status_code, 409)

    def test_owner_checks_cover_all_audio_actions(self):
        other = scene.make(video=self.video_for(owner=user.make()))
        self.assertIn(self.client.get(self.url("scene-waveform", other)).status_code, (403, 404))
        self.assertIn(self.client.patch(self.url("scene-audio", other), {"fade_in": 1}, format="json").status_code, (403, 404))
        self.assertIn(self.client.delete(self.url("scene-voiceover", other)).status_code, (403, 404))

    def test_preview_and_renderer_share_crossfade_plan(self):
        self.scene.audio_settings = {"trim_start": 1, "trim_end": 3, "crossfade": 0.5}
        self.scene.save()
        second = scene.make(video=self.video, file="voice.wav", is_last=False)
        segments = scene_audio_segments([self.scene, second])
        plan = voice_tracks(segments)
        self.assertEqual(plan[1]["start"], 1.5)
        self.assertEqual(plan[0]["fade_out"], 0.5)
        self.assertEqual(plan[1]["fade_in"], 0.5)
        response = self.client.get(reverse("video-preview", args=[self.video.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["audio_tracks"], plan)
        mixed, resources = compose_edited_audio([self.scene, second], [(None, 2), (None, 4)])
        try:
            self.assertEqual(mixed.duration, 6)
            self.assertTrue(np.any(np.abs(mixed.get_frame(0.5)) > 0.01))
            self.assertTrue(np.all(np.abs(mixed.get_frame(5.8)) < 0.001))
        finally:
            mixed.close()
            for resource in resources:
                resource.close()

    def test_pause_prevents_crossfade(self):
        self.scene.pause_after = 1
        self.scene.audio_settings = {"crossfade": 0.5}
        self.scene.save()
        second = scene.make(video=self.video, file="voice.wav", is_last=False)
        plan = voice_tracks(scene_audio_segments([self.scene, second]))
        self.assertEqual(plan[1]["start"], 5)
        self.assertEqual(plan[1]["fade_in"], 0)

    def test_music_envelope_recovers_and_preserves_level_without_speech(self):
        settings = {"music_volume": 0.8, "music_ducking": True, "music_fade_in": 0, "music_fade_out": 0}
        values = music_gain(np.array([1, 1.9, 3, 4.4, 5]), 10, settings, [[2, 4]])
        np.testing.assert_allclose(values, [0.8, 0.5, 0.2, 0.5, 0.8])
        self.assertEqual(music_gain(3, 10, settings, []), 0.8)

    def test_music_settings_preserve_unrelated_options(self):
        response = self.client.patch(reverse("video-audio", args=[self.video.pk]), {"music_ducking": True, "duck_release": 1.2}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["settings"]["narration"])
        self.assertTrue(response.data["settings"]["music_ducking"])

    def test_uploaded_voice_plays_when_generated_narration_is_off(self):
        self.video.settings = {"narration": False}
        self.video.save()
        self.scene.voiceover = "voice.wav"
        self.scene.save()
        response = self.client.get(reverse("video-preview", args=[self.video.pk]))
        self.assertEqual(len(response.data["audio_tracks"]), 1)

    def test_real_video_render_contains_edited_voice_and_ducked_music(self):
        from ...baker_recipes import music
        from ...utils.composer.render import make_video
        from ...utils.timing import media_timing
        self.scene.audio_settings = {"trim_start": 1, "trim_end": 3, "fade_in": 0.2, "crossfade": 0.5}
        self.scene.save()
        second = scene.make(video=self.video, file="voice.wav", is_last=False,
                            audio_settings={"trim_start": 1, "trim_end": 3, "fade_out": 0.2})
        self.video.music = music.make(file="voice.wav")
        self.video.settings = {"music_ducking": True, "music_fade_in": 0.2, "music_fade_out": 0.2}
        self.video.dir_name = str(Path(self.directory.name, "render"))
        Path(self.video.dir_name).mkdir()
        self.video.save()
        with patch("apps.videomanagement.utils.composer.render.output_size", return_value=(32, 18)):
            result = make_video(self.video)
        self.assertEqual(result.status, VideoStatus.COMPLETED)
        metadata = media_timing(result.output.path)
        self.assertAlmostEqual(metadata["duration"], 4, delta=0.05)
        self.assertAlmostEqual(metadata["audio_duration"], 4, delta=0.05)
