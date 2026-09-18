import json

from django.test import SimpleTestCase

from ..defaults import script_format


class ScriptFormatTests(SimpleTestCase):
    def test_asks_for_a_still_by_default(self):
        brief = script_format()

        self.assertIn("a description of an image that illustrates it", brief)
        self.assertNotIn("camera move", brief)

    def test_asks_for_footage_for_a_video_provider(self):
        brief = script_format(video=True)

        self.assertIn("live-action shot", brief)
        # A still model would waste most of its value on this direction.
        self.assertIn("camera move", brief)

    def test_asks_for_a_spoken_line_when_there_is_narration(self):
        self.assertIn('"sentence"', script_format(narration=True))

    def test_drops_the_spoken_line_when_there_is_no_narration(self):
        brief = script_format(narration=False)

        self.assertNotIn('"sentence"', brief)
        self.assertIn("there is no narration", brief)

    def test_keeps_the_same_json_shape_for_every_combination(self):
        # The pipeline walks one fixed scenes -> sentences structure, whatever the
        # brief asked the model to fill it with.
        for video in (False, True):
            for narration in (False, True):
                with self.subTest(video=video, narration=narration):
                    brief = script_format(video=video, narration=narration)
                    shape = brief[brief.index("{") : brief.rindex("}") + 1]

                    parsed = json.loads(shape)

                    self.assertEqual(
                        list(parsed), ["title", "target_audience", "topic", "scenes"]
                    )
                    self.assertIn("sentences", parsed["scenes"][0])
                    self.assertIn(
                        "image_description", parsed["scenes"][0]["sentences"][0]
                    )
