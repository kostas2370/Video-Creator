import subprocess
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings

from apps.usermanagement.baker_recipes import user
from apps.videomanagement.baker_recipes import scene, video
from apps.videomanagement.services.captions.alignment import (
    align_scene_narration,
    aligned_words,
)
from apps.videomanagement.services.captions.subtitles import (
    export_subtitles,
    scene_cues,
)
from apps.videomanagement.services.captions.transcription import normalize_words
from apps.videomanagement.services.scenes.narration import narrate_scene
from apps.videomanagement.services.videos.preview import preview_timeline
from apps.videomanagement.utils.composer.render import write_captions


class SpeechAlignmentTests(TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        override = override_settings(MEDIA_ROOT=directory.name)
        override.enable()
        self.addCleanup(override.disable)
        self.audio = Path(directory.name, "speech.wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                        "sine=frequency=440:duration=4", str(self.audio)],
                       capture_output=True, check=True, timeout=20)
        self.video = video.make(created_by=user.make(), settings={"subtitles": True, "platform": "TIKTOK"})
        self.scene = scene.make(video=self.video, file=str(self.audio), text="Hello world. Again!")
        self.client = self.enterContext(patch("apps.videomanagement.services.captions.transcription.OpenAI"))
        self.key = self.enterContext(patch("apps.videomanagement.services.captions.alignment.ApiKeys.key_for", return_value="test-key"))
        self.usage = self.enterContext(patch("apps.videomanagement.services.captions.transcription.record_usage"))
        self.transcribe = self.client.return_value.audio.transcriptions.create
        self.transcribe.return_value = SimpleNamespace(words=[
            SimpleNamespace(word="Hello", start=0.3, end=0.6),
            SimpleNamespace(word="world.", start=0.9, end=1.3),
            SimpleNamespace(word="Again!", start=2.5, end=3.1),
        ])

    def test_measured_timing_is_persisted_and_reused_for_highlights_and_srt(self):
        align_scene_narration(self.scene)
        self.scene.refresh_from_db()
        cues = scene_cues(self.scene, duration=4, offset=10, highlight=True)
        self.assertEqual([(cue.start, cue.end, cue.active_word) for cue in cues],
                         [(10.3, 10.9, 0), (10.9, 11.3, 1), (12.5, 13.1, 0)])
        self.assertEqual(cues[0].text, "Hello world.")
        align_scene_narration(self.scene)
        self.transcribe.assert_called_once()
        self.assertEqual(self.transcribe.call_args.kwargs["timestamp_granularities"], ["word"])
        self.usage.assert_called_once_with(self.video.created_by, "stt", "OPENAI", "whisper-1", seconds=4)
        srt = export_subtitles(self.video)
        self.assertIn("00:00:00,300 --> 00:00:01,300", srt)
        self.assertIn("00:00:02,500 --> 00:00:03,100", srt)
        self.assertEqual(srt.count("Hello world."), 1)

    def test_trim_delay_and_duration_limit_apply_to_measured_words(self):
        align_scene_narration(self.scene)
        self.scene.audio_settings = {"trim_start": 0.5, "trim_end": 3.5, "delay": 0.4, "duration": 1.1}
        cues = scene_cues(self.scene, duration=4, offset=2, highlight=True)
        self.assertEqual(len(cues), 2)
        self.assertAlmostEqual(cues[0].start, 2.4)
        self.assertAlmostEqual(cues[-1].end, 3.1)
        self.assertEqual(cues[-1].active_word, 1)

    def test_preview_and_burned_in_captions_use_saved_word_boundaries(self):
        align_scene_narration(self.scene)
        timeline = preview_timeline(self.video)
        self.assertEqual(timeline.captions[0].start, 0.3)
        self.assertEqual(timeline.captions[1].start, 0.9)
        destination = self.audio.with_name("captions.ass")
        write_captions(destination, timeline.segments, (1080, 1920))
        exported = destination.read_text()
        self.assertIn("0:00:00.30,0:00:00.90", exported)
        self.assertIn("0:00:02.50,0:00:03.10", exported)
        self.assertIn(r"{\1c&H0046E8FF&}WORLD.", exported)
        self.transcribe.assert_called_once()

    def test_replacing_audio_or_editing_script_invalidates_saved_timing(self):
        align_scene_narration(self.scene)
        self.scene.text = "A replacement script."
        self.assertEqual(aligned_words(self.scene), [])
        self.scene.text = "Hello world. Again!"
        self.audio.touch()
        self.assertEqual(aligned_words(self.scene), [])
        align_scene_narration(self.scene)
        self.assertEqual(self.transcribe.call_count, 2)

    def test_voiceover_takes_precedence_over_generated_narration(self):
        align_scene_narration(self.scene)
        other = self.audio.with_name("recording.wav")
        other.write_bytes(self.audio.read_bytes())
        self.scene.voiceover = str(other)
        self.assertEqual(aligned_words(self.scene), [])
        align_scene_narration(self.scene)
        self.assertEqual(len(aligned_words(self.scene)), 3)
        self.assertEqual(self.transcribe.call_count, 2)

    def test_missing_key_disabled_captions_and_provider_failure_keep_estimated_timing(self):
        self.key.return_value = None
        align_scene_narration(self.scene)
        self.transcribe.assert_not_called()
        self.key.return_value = "test-key"
        self.video.settings["subtitles"] = False
        align_scene_narration(self.scene)
        self.transcribe.assert_not_called()
        self.video.settings["subtitles"] = True
        self.transcribe.side_effect = RuntimeError("Provider unavailable")
        align_scene_narration(self.scene)
        self.assertEqual(aligned_words(self.scene), [])
        self.assertEqual(scene_cues(self.scene, duration=4)[0].start, 0)

    def test_narration_generation_automatically_aligns_the_saved_audio(self):
        with patch("apps.videomanagement.services.scenes.narration.save", return_value=str(self.audio)):
            narrate_scene(self.scene, self.video.voice_model, self.audio.parent, user=self.video.created_by)
        self.scene.refresh_from_db()
        self.assertEqual(len(aligned_words(self.scene)), 3)

    def test_bad_word_intervals_are_discarded_and_clamped(self):
        self.transcribe.return_value.words = [
            SimpleNamespace(word="bad", start=float("nan"), end=1),
            SimpleNamespace(word="Hello there", start=-0.1, end=0.6),
            SimpleNamespace(word="overlap", start=0.2, end=0.8),
            SimpleNamespace(word="end", start=3.5, end=8),
            SimpleNamespace(word="outside", start=9, end=10),
        ]
        align_scene_narration(self.scene)
        words = aligned_words(self.scene)
        self.assertEqual([word["text"] for word in words], ["Hello", "there", "overlap", "end"])
        self.assertEqual(words[0]["start"], 0)
        self.assertEqual(words[2]["start"], 0.6)
        self.assertEqual(words[-1]["end"], 4)


class TranscriptionNormalizationTests(SimpleTestCase):
    def test_nonfinite_overlapping_and_multiword_results_are_normalized(self):

        words = normalize_words([
            SimpleNamespace(word="bad", start=float("nan"), end=0.5),
            SimpleNamespace(word="bad", start=0.2, end=float("nan")),
            SimpleNamespace(word="Hello there", start=-1, end=0.6),
            SimpleNamespace(word="overlap", start=0.2, end=0.8),
            SimpleNamespace(word="last", start=0.8, end=2),
        ], 1.23456)
        self.assertEqual([word["text"] for word in words], ["Hello", "there", "overlap", "last"])
        self.assertEqual(words[-1]["end"], 1.23456)
        self.assertEqual(words[2]["start"], 0.6)
