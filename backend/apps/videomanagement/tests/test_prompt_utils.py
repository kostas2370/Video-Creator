from django.test import SimpleTestCase

from ..utils.prompt_utils import (
    format_dalle_prompt,
    format_prompt,
    format_sora_prompt,
    format_update_form,
    scene_text,
)


class FormatPromptTests(SimpleTestCase):
    def test_carries_every_part_of_the_brief_into_the_prompt(self):
        prompt = format_prompt(
            template_format="a structure",
            template_category="EDUCATIONAL",
            userprompt="explain photosynthesis",
            title="How Plants Eat",
            target_audience="children",
        )

        self.assertIn("a structure", prompt)
        self.assertIn("EDUCATIONAL", prompt)
        self.assertIn("explain photosynthesis", prompt)
        self.assertIn("How Plants Eat", prompt)
        self.assertIn("children", prompt)

    def test_hands_the_title_back_to_the_model_when_none_was_given(self):
        prompt = format_prompt(template_format="", template_category="")

        self.assertIn("The title will be selected by you", prompt)

    def test_hands_the_audience_back_to_the_model_when_none_was_given(self):
        prompt = format_prompt(template_format="", template_category="")

        self.assertIn("Select an appropriate target audience", prompt)


class SceneTextTests(SimpleTestCase):
    """The text a Scene row is found by later, so it can never come back empty."""

    def test_prefers_the_narration(self):
        sentence = {"sentence": " spoken line ", "image_description": "a shot"}

        self.assertEqual(scene_text(sentence), "spoken line")

    def test_falls_back_to_the_shot_description_when_nothing_is_spoken(self):
        # Narration off: the script is never asked for a spoken line.
        self.assertEqual(scene_text({"image_description": " a shot "}), "a shot")

    def test_falls_back_when_the_narration_is_present_but_empty(self):
        sentence = {"sentence": "", "image_description": "a shot"}

        self.assertEqual(scene_text(sentence), "a shot")


class FormatSoraPromptTests(SimpleTestCase):
    def test_describes_the_shot_in_prose(self):
        prompt = format_sora_prompt(title="", image_description=" a cat naps.")

        self.assertEqual(prompt, "Cinematic video shot: a cat naps.")

    def test_names_the_video_when_there_is_a_title(self):
        prompt = format_sora_prompt(title="Cats", image_description="a cat naps")

        self.assertIn("From a video titled 'Cats'.", prompt)

    def test_repeats_the_style_on_every_shot(self):
        prompt = format_sora_prompt(
            title="Cats", image_description="a cat naps", style=" warm film grain"
        )

        self.assertTrue(prompt.endswith("warm film grain"))

    def test_omits_an_empty_title_rather_than_sending_a_stray_label(self):
        prompt = format_sora_prompt(title="", image_description="a cat naps")

        self.assertNotIn("titled", prompt)


class OtherPromptTests(SimpleTestCase):
    def test_dalle_prompt_labels_the_title_and_description(self):
        prompt = format_dalle_prompt(title="Cats", image_description="a cat naps")

        self.assertIn("Title : Cats", prompt)
        self.assertIn("Image Description:a cat naps", prompt)

    def test_update_form_asks_for_a_rewrite_of_the_same_length(self):
        prompt = format_update_form("the old line", "make it funnier")

        self.assertIn("the old line", prompt)
        self.assertIn("make it funnier", prompt)
        self.assertIn("around the same size", prompt)
