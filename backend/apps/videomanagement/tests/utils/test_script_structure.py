import json

from django.test import SimpleTestCase

from ...utils.prompt_utils import build_script_prompt


class ScriptFormatTests(SimpleTestCase):
    def test_asks_for_a_still_by_default(self):
        brief = build_script_prompt()

        self.assertIn("a description of an image that illustrates it", brief)
        self.assertNotIn("camera move", brief)

    def test_asks_for_footage_for_a_video_provider(self):
        brief = build_script_prompt(video=True)

        self.assertIn("video shot", brief)
        # A still model would waste most of its value on this direction.
        self.assertIn("camera move", brief)

    def test_asks_for_a_spoken_line_when_there_is_narration(self):
        self.assertIn('"sentence"', build_script_prompt(narration=True))

    def test_drops_the_spoken_line_when_there_is_no_narration(self):
        brief = build_script_prompt(narration=False)

        self.assertNotIn('"sentence"', brief)
        self.assertIn("there is no narration", brief)

    def test_preserves_scene_shape_and_adds_continuity_only_for_ai(self):
        for mode in ("AI", "WEB"):
            for video in (False, True):
                for narration in (False, True):
                    with self.subTest(mode=mode, video=video, narration=narration):
                        brief = build_script_prompt(
                            image_mode=mode,
                            video=video,
                            narration=narration,
                        )
                        shape = brief[brief.index("{") : brief.rindex("}") + 1]
                        parsed = json.loads(shape)
                        keys = ["title", "target_audience", "topic"]
                        if mode == "AI":
                            keys.append("visual_continuity")
                        self.assertEqual(list(parsed), [*keys, "scenes"])
                        self.assertIn("sentences", parsed["scenes"][0])
                        self.assertIn(
                            "image_description",
                            parsed["scenes"][0]["sentences"][0],
                        )
