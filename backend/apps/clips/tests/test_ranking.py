import copy
import json
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.clips.highlights import suggest_clips, validate_ranking


def assessment(index, **changes):
    return {
        "index": index,
        "hook": 4,
        "context": 4,
        "payoff": 4,
        "relevance": 3,
        "duplicate_of": None,
        **changes,
    }


class ClipRankingTests(SimpleTestCase):
    def test_allows_fewer_good_clips_than_requested_in_best_first_order(self):
        result = validate_ranking(
            {"assessments": [assessment(i) for i in range(3)], "indices": [2, 0]},
            3,
            3,
            False,
        )
        self.assertEqual(result, [2, 0])

    def test_does_not_keep_a_strong_hook_without_context_or_a_payoff(self):
        result = validate_ranking(
            {
                "assessments": [
                    assessment(0, hook=5, context=1),
                    assessment(1, hook=5, payoff=2),
                    assessment(2),
                ],
                "indices": [0, 1, 2],
            },
            3,
            3,
            False,
        )
        self.assertEqual(result, [2])

    def test_drops_an_irrelevant_clip_only_when_a_brief_is_present(self):
        data = {"assessments": [assessment(0, relevance=1)], "indices": [0]}
        self.assertEqual(validate_ranking(data, 1, 1, True), [])
        self.assertEqual(validate_ranking(data, 1, 1, False), [0])

    def test_keeps_one_representative_of_each_repeated_point(self):
        data = {
            "assessments": [
                assessment(0),
                assessment(1, duplicate_of=0),
                assessment(2),
            ],
            "indices": [1, 0, 2],
        }
        self.assertEqual(validate_ranking(data, 3, 3, False), [1, 2])

    def test_allows_no_usable_match(self):
        data = {"assessments": [assessment(0, context=1)], "indices": []}
        self.assertEqual(validate_ranking(data, 1, 1, False), [])

    def test_rejects_incomplete_out_of_range_boolean_and_duplicate_ratings(self):
        original = {
            "assessments": [assessment(0), assessment(1)],
            "indices": [0],
        }
        invalid = []
        for field in ("hook", "context", "payoff", "relevance"):
            for value in (True, 3.5, "4", -1, 6, None):
                data = copy.deepcopy(original)
                data["assessments"][0][field] = value
                invalid.append(data)
            data = copy.deepcopy(original)
            del data["assessments"][0][field]
            invalid.append(data)
        for indices in ([True], [2], [-1], [0, 0], [0, 1, 0], None):
            invalid.append({**original, "indices": indices})
        for reviews in (
            [assessment(0)],
            [assessment(0), assessment(0)],
            [assessment(True), assessment(1)],
            [assessment(0, duplicate_of=2), assessment(1)],
            [assessment(0, duplicate_of=True), assessment(1)],
            [assessment(0, duplicate_of=0), assessment(1)],
            [assessment(0, duplicate_of=1), assessment(1, duplicate_of=0)],
            [None, assessment(1)],
        ):
            invalid.append({**original, "assessments": reviews})
        for data in invalid:
            with self.subTest(data=data), self.assertRaises(ValueError):
                validate_ranking(data, 2, 2, False)

    def project(self, count=3, word_count=80):
        words = [
            {"text": f"word{index}.", "start": float(index), "end": index + 0.8}
            for index in range(word_count)
        ]
        return SimpleNamespace(
            words=words,
            clip_count=count,
            min_duration=10,
            max_duration=20,
            extraction_prompt="Funny moments",
            created_by=None,
        )

    def candidate(self, first, title):
        return {
            "first_word": first,
            "last_word": first + 12,
            "title": title,
            "reason": "Exciting!",
        }

    def test_reviews_actual_excerpts_even_when_the_candidate_count_fits_the_request(
        self,
    ):
        project = self.project()
        extraction = {
            "clips": [self.candidate(0, "Big payoff"), self.candidate(30, "Another")]
        }
        ranking = {
            "assessments": [assessment(0, payoff=1), assessment(1)],
            "indices": [0, 1],
        }
        with patch(
            "apps.clips.highlights.get_update_sentence",
            side_effect=[json.dumps(extraction), json.dumps(ranking)],
        ) as provider:
            result = suggest_clips(project)
        self.assertEqual([item["title"] for item in result], ["Another"])
        payload = json.loads(provider.call_args.args[0].split("\n", 1)[1])
        self.assertEqual(payload["extraction_brief"], "Funny moments")
        self.assertEqual(
            payload["candidates"][0]["transcript"],
            " ".join(word["text"] for word in project.words[:13]),
        )
        self.assertNotIn("transcript", result[0])
        self.assertEqual(set(result[0]), {"start", "end", "title", "reason"})

    def test_can_discard_repeated_points_at_nonoverlapping_source_times(self):
        project = self.project(count=2)
        extraction = {"clips": [self.candidate(0, "A"), self.candidate(40, "B")]}
        ranking = {
            "assessments": [assessment(0), assessment(1, duplicate_of=0)],
            "indices": [0, 1],
        }
        with patch(
            "apps.clips.highlights.get_update_sentence",
            side_effect=[json.dumps(extraction), json.dumps(ranking)],
        ):
            result = suggest_clips(project)
        self.assertEqual([item["title"] for item in result], ["A"])

    def test_stops_before_a_paid_review_when_the_job_is_superseded(self):
        extraction = {"clips": [self.candidate(0, "A"), self.candidate(40, "B")]}
        with (
            patch(
                "apps.clips.highlights.get_update_sentence",
                return_value=json.dumps(extraction),
            ) as provider,
            patch("apps.clips.highlights.RANKING_BATCH_SIZE", 2),
            patch("apps.clips.highlights.rank_candidates") as rank,
        ):
            current = iter([True, False])
            result = suggest_clips(self.project(), is_current=lambda: next(current))
        self.assertEqual(result, [])
        provider.assert_called_once()
        rank.assert_not_called()

    def test_bounds_review_batches_and_reviews_survivors_together(self):
        project = self.project(count=1, word_count=2400)
        responses = [
            json.dumps({"clips": [self.candidate(first, str(first))]})
            for first in (0, 1100, 2100)
        ]
        with (
            patch("apps.clips.highlights.get_update_sentence", side_effect=responses),
            patch("apps.clips.highlights.RANKING_BATCH_SIZE", 2),
            patch(
                "apps.clips.highlights.rank_candidates",
                side_effect=lambda project, batch: batch[:1],
            ) as rank,
        ):
            result = suggest_clips(project)
        self.assertEqual([len(call.args[1]) for call in rank.call_args_list], [2, 1, 2])
        self.assertEqual(result[0]["start"], 0)

    def test_fast_mode_skips_review_and_keeps_the_requested_result_limit(self):
        project = self.project(count=1, word_count=1400)
        project.selection_mode = "fast"
        responses = [
            json.dumps({"clips": [self.candidate(first, str(first))]})
            for first in (0, 1100)
        ]
        with (
            patch(
                "apps.clips.highlights.get_update_sentence", side_effect=responses
            ) as provider,
            patch("apps.clips.highlights.rank_candidates") as rank,
        ):
            result = suggest_clips(project)
        self.assertEqual(len(result), 1)
        self.assertEqual(provider.call_count, 2)
        rank.assert_not_called()

    def test_strict_mode_reviews_even_a_single_candidate_and_drops_adequate_context(
        self,
    ):
        project = self.project()
        project.selection_mode = "strict"
        extraction = {"clips": [self.candidate(0, "A")]}
        ranking = {
            "assessments": [assessment(0, context=3, relevance=4)],
            "indices": [0],
        }
        with patch(
            "apps.clips.highlights.get_update_sentence",
            side_effect=[json.dumps(extraction), json.dumps(ranking)],
        ) as provider:
            self.assertEqual(suggest_clips(project), [])
        self.assertEqual(provider.call_count, 2)
        self.assertIn("context >= 4", provider.call_args.args[0])

    def test_strict_mode_keeps_a_strong_candidate(self):
        project = self.project()
        project.selection_mode = "strict"
        extraction = {"clips": [self.candidate(0, "A")]}
        ranking = {"assessments": [assessment(0, relevance=4)], "indices": [0]}
        with patch(
            "apps.clips.highlights.get_update_sentence",
            side_effect=[json.dumps(extraction), json.dumps(ranking)],
        ):
            self.assertEqual(suggest_clips(project)[0]["title"], "A")

    def test_a_focus_preset_enforces_relevance_without_a_written_brief(self):
        project = self.project()
        project.clip_focus = "funny"
        project.extraction_prompt = None
        extraction = {"clips": [self.candidate(0, "A"), self.candidate(40, "B")]}
        ranking = {
            "assessments": [assessment(0, relevance=1), assessment(1)],
            "indices": [0, 1],
        }
        with patch(
            "apps.clips.highlights.get_update_sentence",
            side_effect=[json.dumps(extraction), json.dumps(ranking)],
        ) as provider:
            result = suggest_clips(project)
        self.assertEqual([item["title"] for item in result], ["B"])
        for call in provider.call_args_list:
            self.assertIn("jokes, comic exchanges", call.args[0])
            self.assertIn("explicit extraction brief takes priority", call.args[0])

    def test_all_focus_presets_are_applied_without_rewriting_the_user_brief(self):
        from apps.clips.highlights import FOCUS_GUIDANCE

        for focus, guidance in FOCUS_GUIDANCE.items():
            with self.subTest(focus=focus):
                project = self.project()
                project.clip_focus = focus
                with patch(
                    "apps.clips.highlights.get_update_sentence",
                    return_value='{"clips": []}',
                ) as provider:
                    self.assertEqual(suggest_clips(project), [])
                self.assertIn(guidance, provider.call_args.args[0])
                payload = json.loads(provider.call_args.args[0].split("\n", 1)[1])
                self.assertEqual(payload["extraction_brief"], "Funny moments")
