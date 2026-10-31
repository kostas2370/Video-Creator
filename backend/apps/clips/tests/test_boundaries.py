import json
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.clips.boundaries import refine_boundaries
from apps.clips.highlights import suggest_clips


class ClipBoundaryTests(SimpleTestCase):
    def setUp(self):
        self.words = [
            {"text": f"word{index}", "start": float(index), "end": index + 0.8}
            for index in range(40)
        ]
        self.words[9]["text"] = "Introduction."
        self.words[27]["text"] = "payoff."

    def test_extends_a_cut_to_the_nearest_sentence_opening_and_ending(self):
        self.assertEqual(refine_boundaries(self.words, 12, 24, 10, 20), (10, 27))

    def test_preserves_an_already_complete_sentence(self):
        self.assertEqual(refine_boundaries(self.words, 10, 27, 10, 20), (10, 27))

    def test_fixes_one_edge_when_completing_both_would_exceed_the_maximum(self):
        self.assertEqual(refine_boundaries(self.words, 12, 24, 10, 15), (10, 24))

    def test_does_not_extend_more_than_five_seconds_per_edge(self):
        self.words[9]["text"] = "Introduction"
        self.words[27]["text"] = "payoff"
        self.assertEqual(refine_boundaries(self.words, 12, 24, 10, 30), (12, 24))

    def test_uses_pauses_when_the_transcript_has_no_punctuation(self):
        self.words[9]["text"] = "Introduction"
        self.words[27]["text"] = "payoff"
        self.words[9]["end"] = 9.1
        self.words[27]["end"] = 27.1
        self.assertEqual(refine_boundaries(self.words, 12, 24, 10, 20), (10, 27))

    def test_recognizes_sentence_punctuation_before_closing_quotes(self):
        for ending in ("done.”", "τέλος!»", "終わり。", "结束！", "끝？", "fin…", "τέλος;»", "τέλος;»"):
            with self.subTest(ending=ending):
                self.words[27]["text"] = ending
                self.assertEqual(
                    refine_boundaries(self.words, 12, 24, 10, 20), (10, 27)
                )

    def test_trims_to_a_complete_ending_when_expansion_cannot_fit(self):
        self.words[22]["text"] = "Complete."
        self.assertEqual(refine_boundaries(self.words, 10, 24, 10, 15), (10, 22))

    def test_preserves_selected_speech_when_expansion_and_trimming_both_fit(self):
        self.words[22]["text"] = "Complete."
        self.assertEqual(refine_boundaries(self.words, 10, 24, 10, 20), (10, 27))

    def test_does_not_trim_below_the_minimum(self):
        self.words[22]["text"] = "Complete."
        self.assertEqual(refine_boundaries(self.words, 10, 24, 14, 15), (10, 24))

    def test_can_trim_an_incomplete_opening(self):
        self.words[14]["text"] = "Previous."
        self.assertEqual(refine_boundaries(self.words, 12, 27, 10, 16), (15, 27))

    def test_handles_source_start_and_end(self):
        self.assertEqual(refine_boundaries(self.words, 0, 39, 10, 40), (0, 39))

    def test_keeps_original_decimal_timestamps_in_suggestions(self):
        project = SimpleNamespace(
            words=self.words,
            clip_count=1,
            min_duration=10,
            max_duration=20,
            extraction_prompt="",
            created_by=None,
        )
        self.words[10]["start"] = 10.125
        self.words[27]["end"] = 27.875
        response = json.dumps(
            {
                "clips": [
                    {"first_word": 12, "last_word": 24, "title": "A", "reason": "B"}
                ]
            }
        )
        with patch(
            "apps.clips.highlights.get_update_sentence", return_value=response
        ) as provider:
            result = suggest_clips(project)
        self.assertEqual((result[0]["start"], result[0]["end"]), (10.125, 27.875))
        provider.assert_called_once()

    def test_refines_later_windows_using_absolute_source_timestamps(self):
        words = [
            {"text": "word", "start": float(index), "end": index + 0.8}
            for index in range(1400)
        ]
        words[1099]["text"] = "Opening."
        words[1115]["text"] = "Ending."
        project = SimpleNamespace(
            words=words,
            clip_count=1,
            min_duration=10,
            max_duration=20,
            extraction_prompt="",
            created_by=None,
        )
        response = json.dumps(
            {
                "clips": [
                    {"first_word": 1102, "last_word": 1114, "title": "A", "reason": "B"}
                ]
            }
        )
        with patch(
            "apps.clips.highlights.get_update_sentence",
            side_effect=['{"clips": []}', response],
        ):
            result = suggest_clips(project)
        self.assertEqual((result[0]["start"], result[0]["end"]), (1100, 1115.8))

    def test_window_start_is_not_treated_as_a_sentence_opening(self):
        words = [
            {"text": "word", "start": float(index), "end": index + 0.8}
            for index in range(1250)
        ]
        words[997]["text"] = "Previous."
        words[1015]["text"] = "Complete."
        project = SimpleNamespace(
            words=words, clip_count=1, min_duration=10, max_duration=20,
            extraction_prompt="", created_by=None,
        )
        response = json.dumps({"clips": [{
            "first_word": 1000, "last_word": 1015, "title": "A", "reason": "B",
        }]})
        with patch(
            "apps.clips.highlights.get_update_sentence",
            side_effect=['{"clips": []}', response],
        ):
            result = suggest_clips(project)
        self.assertEqual((result[0]["start"], result[0]["end"]), (998, 1015.8))

    def test_window_end_is_not_treated_as_a_sentence_ending(self):
        words = [
            {"text": "word", "start": float(index), "end": index + 0.8}
            for index in range(1250)
        ]
        words[1183]["text"] = "Previous."
        words[1202]["text"] = "Complete."
        project = SimpleNamespace(
            words=words, clip_count=1, min_duration=10, max_duration=20,
            extraction_prompt="", created_by=None,
        )
        response = json.dumps({"clips": [{
            "first_word": 1184, "last_word": 1199, "title": "A", "reason": "B",
        }]})
        with patch(
            "apps.clips.highlights.get_update_sentence",
            side_effect=[response, '{"clips": []}'],
        ):
            result = suggest_clips(project)
        self.assertEqual((result[0]["start"], result[0]["end"]), (1184, 1202.8))

    def test_removes_candidates_that_become_duplicates_after_expansion(self):
        self.words[32]["text"] = "Next."
        project = SimpleNamespace(
            words=self.words,
            clip_count=2,
            min_duration=10,
            max_duration=30,
            extraction_prompt="",
            created_by=None,
        )
        response = json.dumps(
            {
                "clips": [
                    {"first_word": 12, "last_word": 22, "title": "A", "reason": "B"},
                    {"first_word": 18, "last_word": 28, "title": "C", "reason": "D"},
                ]
            }
        )
        with patch("apps.clips.highlights.get_update_sentence", return_value=response):
            result = suggest_clips(project)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "A")

    def test_does_not_rescue_invalid_model_ranges_by_expanding_them(self):
        project = SimpleNamespace(
            words=self.words,
            clip_count=1,
            min_duration=10,
            max_duration=20,
            extraction_prompt="",
            created_by=None,
        )
        response = json.dumps(
            {
                "clips": [
                    {"first_word": 12, "last_word": 13, "title": "A", "reason": "B"}
                ]
            }
        )
        with patch("apps.clips.highlights.get_update_sentence", return_value=response):
            self.assertEqual(suggest_clips(project), [])
