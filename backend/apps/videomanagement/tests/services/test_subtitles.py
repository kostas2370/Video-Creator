from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from ...services.subtitles import caption_phrases, scene_cues, cues_to_srt, CaptionCue, srt_timestamp


class CaptionCueTests(SimpleTestCase):
    def test_long_dialogue_is_split_without_losing_words(self):
        text = "This is the first sentence. " + "A longer explanation with several useful details for the viewer " * 8
        phrases = caption_phrases(text)
        self.assertGreater(len(phrases), 5)
        self.assertEqual(" ".join(" ".join(phrases).split()), " ".join(text.split()))
        for phrase in phrases:
            self.assertLessEqual(len(phrase.splitlines()), 2)
            self.assertTrue(all(len(line) <= 32 for line in phrase.splitlines()))
            self.assertLessEqual(len(phrase.split()), 10)
        self.assertEqual(phrases[0], "This is the first sentence.")

    def test_unicode_and_long_tokens_fit_the_caption_box(self):
        phrases = caption_phrases("Γεια σου κόσμε. " + "α" * 150)
        self.assertEqual(phrases[0], "Γεια σου κόσμε.")
        self.assertEqual("".join(phrases[1:]).replace("\n", ""), "α" * 150)
        self.assertTrue(all(len(phrase.splitlines()) <= 2 for phrase in phrases))

    def test_cues_cover_only_narration_and_keep_relative_order(self):
        scene = SimpleNamespace(text="Hello there. A much longer sentence for the viewer.", video=SimpleNamespace(settings={}))
        cues = scene_cues(scene, duration=6, offset=10.75)
        self.assertEqual(len(cues), 2)
        self.assertEqual(cues[0].start, 10.75)
        self.assertEqual(cues[-1].end, 16.75)
        self.assertEqual(cues[0].end, cues[1].start)
        self.assertLess(cues[0].end - cues[0].start, cues[1].end - cues[1].start)

    def test_missing_or_disabled_narration_has_no_captions(self):
        scene = SimpleNamespace(text="Hello.", video=SimpleNamespace(settings={}))
        with patch("apps.videomanagement.services.subtitles.narration_duration", return_value=None):
            self.assertEqual(scene_cues(scene), [])
        scene.video.settings = {"narration": False}
        self.assertEqual(scene_cues(scene, duration=4), [])
        self.assertEqual(scene_cues(scene, duration=0), [])

    def test_srt_rounds_with_carry_and_preserves_utf8_and_line_breaks(self):
        self.assertEqual(srt_timestamp(59.9996), "00:01:00,000")
        self.assertEqual(srt_timestamp(3600.125), "01:00:00,125")
        self.assertEqual(cues_to_srt([CaptionCue(0, 1.25, "Γεια σου\nκόσμε"), CaptionCue(1.5, 2, "Again.")]),
                         "1\n00:00:00,000 --> 00:00:01,250\nΓεια σου\nκόσμε\n\n2\n00:00:01,500 --> 00:00:02,000\nAgain.\n")
