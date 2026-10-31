from types import SimpleNamespace
from unittest.mock import patch

import requests
from django.test import SimpleTestCase, override_settings

from apps.clips.youtube_captions import caption_words, source_tracks, youtube_transcript


def event(start=0, duration=4000, segments=None):
    return {
        "tStartMs": start,
        "dDurationMs": duration,
        "segs": segments
        or [{"utf8": "Hello", "tOffsetMs": 0}, {"utf8": "world", "tOffsetMs": 2000}],
    }


@override_settings(YOUTUBE_CAPTIONS_ENABLED=True)
class YouTubeCaptionTests(SimpleTestCase):
    def track(self, code):
        return SimpleNamespace(
            code=code, url="https://www.youtube.com/api/timedtext?v=example&fmt=srv3"
        )

    def test_uses_word_offsets_and_original_timeline_with_range_clipping(self):
        data = {"events": [event(600000)]}
        self.assertEqual(
            caption_words(data, 601, 603, 604),
            [
                {"text": "Hello", "start": 601, "end": 602},
                {"text": "world", "start": 602, "end": 603},
            ],
        )

    def test_rejects_phrase_only_missing_or_invalid_word_timing(self):
        for data in (
            {"events": [event(segments=[{"utf8": "Hello world"}])]},
            {"events": [event(segments=[{"utf8": "Hello"}, {"utf8": "world"}])]},
            {"events": [event(segments=[{"utf8": "Hello", "tOffsetMs": -100}])]},
            {"events": [event(duration=float("nan"))]},
        ):
            with self.subTest(data=data):
                self.assertIsNone(caption_words(data, 0, 4, 4))

    def test_deduplicates_rolling_captions_and_ignores_display_only_events(self):
        data = {"events": [event(), {"tStartMs": 0}, event()]}
        self.assertEqual(
            [word["text"] for word in caption_words(data, 0, 4, 4)], ["Hello", "world"]
        )

    def test_ignores_phrase_only_captions_outside_the_requested_range(self):
        data = {
            "events": [
                event(0, segments=[{"utf8": "An earlier phrase"}]),
                event(600000),
                event(900000, segments=[{"utf8": "A later phrase"}]),
            ]
        }
        words = caption_words(data, 600, 604, 904)
        self.assertEqual([word["text"] for word in words], ["Hello", "world"])

    def test_conflicting_words_at_the_same_time_fall_back_to_transcription(self):
        data = {
            "events": [event(), event(segments=[{"utf8": "Different", "tOffsetMs": 0}])]
        }
        self.assertIsNone(caption_words(data, 0, 4, 4))

    def test_rejects_tracks_that_do_not_cover_the_requested_section(self):
        data = {"events": [event(0), event(110000)]}
        self.assertIsNone(caption_words(data, 0, 120, 120))
        self.assertIsNone(caption_words({"events": [event()]}, 20, 40, 40))

    def test_chooses_original_language_and_prefers_word_timed_automatic_track(self):
        tracks = [self.track("en"), self.track("el"), self.track("a.el")]
        video = SimpleNamespace(captions=tracks, vid_info={})
        self.assertEqual([track.code for track in source_tracks(video)], ["a.el", "el"])

    def test_uses_default_audio_track_language_when_available(self):
        video = SimpleNamespace(
            captions=[self.track("a.en"), self.track("a.el")],
            vid_info={
                "captions": {
                    "playerCaptionsTracklistRenderer": {
                        "defaultAudioTrackIndex": 1,
                        "audioTracks": [
                            {"defaultCaptionTrackIndex": 0},
                            {"defaultCaptionTrackIndex": 1},
                        ],
                        "captionTracks": [{"vssId": "a.en"}, {"vssId": "a.el"}],
                    }
                }
            },
        )
        self.assertEqual([track.code for track in source_tracks(video)], ["a.el"])

    def test_skips_ambiguous_languages_instead_of_guessing(self):
        video = SimpleNamespace(
            captions=[self.track("en"), self.track("el")], vid_info={}
        )
        self.assertEqual(source_tracks(video), [])

    def test_fetches_json_timing_and_falls_back_on_inaccessible_captions(self):
        project = SimpleNamespace(
            youtube_url="https://youtu.be/abcdefghijk",
            range_start=0,
            range_stop=4,
            duration=4,
        )
        with (
            patch(
                "apps.clips.youtube_captions.YouTube",
                return_value=SimpleNamespace(
                    captions=[self.track("a.el")], vid_info={}
                ),
            ),
            patch("apps.clips.youtube_captions.requests.get") as get,
        ):
            get.return_value.json.return_value = {"events": [event()]}
            words, source = youtube_transcript(project)
            self.assertEqual(len(words), 2)
            self.assertEqual(source, "YouTube captions (el, automatic)")
            self.assertIn("fmt=json3", get.call_args.args[0])
            self.assertNotIn("fmt=srv3", get.call_args.args[0])
            self.assertEqual(get.call_args.kwargs["timeout"], (5, 20))
            get.side_effect = requests.Timeout()
            self.assertIsNone(youtube_transcript(project))

    def test_disabled_captions_and_file_uploads_make_no_youtube_request(self):
        with patch("apps.clips.youtube_captions.YouTube") as youtube:
            self.assertIsNone(youtube_transcript(SimpleNamespace(youtube_url="")))
            with override_settings(YOUTUBE_CAPTIONS_ENABLED=False):
                self.assertIsNone(
                    youtube_transcript(
                        SimpleNamespace(youtube_url="https://youtu.be/abcdefghijk")
                    )
                )
        youtube.assert_not_called()
