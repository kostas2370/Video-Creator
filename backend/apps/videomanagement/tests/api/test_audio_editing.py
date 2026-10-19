
import subprocess
import tempfile
import wave
from pathlib import Path
from unittest.mock import patch

import numpy as np
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse

from apps.usermanagement.baker_recipes import user
from apps.videomanagement.services.scenes.timeline import scene_audio_segments

from ...baker_recipes import music, scene
from ...models import VideoStatus
from ...utils.audio_editing import music_gain, voice_tracks
from ...utils.composer.render import make_video, narration_graph
from ...utils.timing import media_timing
from .base import ApiTestCase


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

    def browser_recording(self, duration=4):
        path = Path(self.directory.name, "recording.webm")
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
             f"sine=frequency=440:duration={duration}", "-c:a", "libopus",
             "-f", "webm", "-live", "1", str(path)],
            capture_output=True, check=True, timeout=60,
        )
        return SimpleUploadedFile("voiceover.webm", path.read_bytes(), content_type="audio/webm;codecs=opus")

    def test_browser_recording_without_duration_can_be_saved_previewed_and_rendered(self):

        upload = self.browser_recording()
        self.assertEqual(media_timing(Path(self.directory.name, "recording.webm")), {})
        response = self.client.post(self.url("scene-voiceover"), {"file": upload}, format="multipart")
        self.assertEqual(response.status_code, 200, response.data)
        self.scene.refresh_from_db()
        self.assertTrue(self.scene.voiceover.name.endswith(".wav"))
        self.assertEqual(self.scene.file.name, "voice.wav")
        self.assertAlmostEqual(response.data["timing"]["duration"], 4, delta=0.05)
        response = self.client.get(self.url("scene-waveform"))
        self.assertEqual(response.status_code, 200)
        self.assertAlmostEqual(response.data["duration"], 4, delta=0.05)
        response = self.client.patch(self.url("scene-audio"), {"trim_start": 1, "trim_end": 3}, format="json")
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse("video-preview", args=[self.video.pk]))
        self.assertEqual(len(response.data["audio_tracks"]), 1)
        self.assertEqual(response.data["audio_tracks"][0]["duration"], 2)
        self.scene.refresh_from_db()
        graph, stream = narration_graph(scene_audio_segments([self.scene]), self.video.settings)
        output = Path(self.directory.name, "recorded-voice.wav")
        graph.run(self.directory.name, output, [stream], ["-c:a", "pcm_s16le"], 2)
        with wave.open(str(output), "rb") as audio:
            samples = np.frombuffer(audio.readframes(audio.getnframes()), dtype="<i2")
            self.assertGreater(np.abs(samples.astype(float)).mean(), 100)

    def test_browser_recordings_still_obey_the_fifteen_minute_limit(self):
        response = self.client.post(self.url("scene-voiceover"), {"file": self.browser_recording(901)}, format="multipart")
        self.assertEqual(response.status_code, 400)
        self.scene.refresh_from_db()
        self.assertFalse(self.scene.voiceover)
        self.assertEqual(self.scene.file.name, "voice.wav")

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
        output = Path(self.directory.name, "mixed.wav")
        graph, stream = narration_graph(segments, self.video.settings)
        graph.run(self.directory.name, output, [stream], ["-c:a", "pcm_s16le", "-ar", "44100"], 6)
        with wave.open(str(output), "rb") as audio:
            self.assertEqual(audio.getnframes() / audio.getframerate(), 6)
            samples = np.frombuffer(audio.readframes(audio.getnframes()), dtype="<i2").reshape(-1, 2) / 32768
        self.assertGreater(np.abs(samples[22050:26460]).mean(), 0.01)
        self.assertLess(np.abs(samples[255780:264600]).mean(), 0.001)

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
        self.scene.audio_settings = {"trim_start": 1, "trim_end": 3, "fade_in": 0.2, "crossfade": 0.5}
        self.scene.save()
        scene.make(video=self.video, file="voice.wav", is_last=False,
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

    def test_ducked_music_recovers_during_voice_silence_in_export(self):
        path = Path(self.directory.name, "music.wav")
        with wave.open(str(path), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(8000)
            tone = 0.2 * np.sin(2 * np.pi * 700 * np.arange(32000) / 8000)
            output.writeframes((tone * 32767).astype("<i2").tobytes())
        self.video.music = music.make(file="music.wav")
        self.video.settings = {"music_ducking": True, "music_volume": 0.5,
                               "music_fade_in": 0, "music_fade_out": 0,
                               "duck_level": 0.25, "duck_release": 0.2}
        self.video.dir_name = str(Path(self.directory.name, "ducking-render"))
        self.video.save()
        with patch("apps.videomanagement.utils.composer.render.output_size", return_value=(32, 18)):
            result = make_video(self.video)
        decoded = subprocess.check_output(["ffmpeg", "-v", "error", "-i", result.output.path,
                                           "-vn", "-ac", "1", "-ar", "8000", "-f", "f32le", "pipe:1"])
        samples = np.frombuffer(decoded, dtype="<f4")
        def music_level(start):
            chunk = samples[int(start * 8000):int((start + 0.5) * 8000)]
            return abs(np.mean(chunk * np.exp(-2j * np.pi * 700 * np.arange(len(chunk)) / 8000)))
        baseline = music_level(0.25)
        self.assertGreater(baseline, 0.01)
        self.assertLess(music_level(1.5) / baseline, 0.4)
        self.assertGreater(music_level(1.5) / baseline, 0.15)
        self.assertAlmostEqual(music_level(3.25) / baseline, 1, delta=0.15)
