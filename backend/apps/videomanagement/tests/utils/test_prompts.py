import json

from django.test import SimpleTestCase

from ...utils.prompt_utils import (
    format_cover_prompt,
    format_image_prompt,
    format_prompt,
    format_scene_draft,
    format_sora_prompt,
    format_update_form,
    scene_text,
)


class FormatPromptTests(SimpleTestCase):
    def test_carries_every_part_of_the_brief_into_the_prompt(self):
        prompt = format_prompt(
            template_format="a structure",
            genre="EDUCATIONAL",
            userprompt="explain photosynthesis",
            title="How Plants Eat",
            target_audience="children",
        )

        self.assertIn("a structure", prompt)
        self.assertIn("EDUCATIONAL", prompt)
        self.assertIn("explain photosynthesis", prompt)
        self.assertIn("How Plants Eat", prompt)
        self.assertIn("children", prompt)

    def test_web_mode_requests_search_terms_without_generation_directions(self):
        from ...defaults import script_format

        for narration in (True, False):
            template = script_format(video=True, narration=narration, image_mode="WEB")
            prompt = format_prompt(template, "", image_mode="WEB")
            self.assertIn("concise image search query", prompt)
            self.assertIn("3–8 words", prompt)
            self.assertNotIn("camera move", template)
            self.assertNotIn("highly detailed visual descriptions", prompt)
            self.assertIn('"image_description"', template)

    def test_ai_mode_preserves_detailed_visual_instructions(self):
        prompt = format_prompt("", "", image_mode="AI")
        self.assertIn("highly detailed visual descriptions", prompt)
        self.assertNotIn("image search query", prompt)

    def test_web_scene_drafts_request_search_terms(self):
        prompt = format_scene_draft("Paris", image_mode="WEB")
        self.assertIn("concise image search query", prompt)
        self.assertNotIn("own visual description", prompt)
        self.assertIn("highly detailed visual descriptions", format_scene_draft("Paris"))

    def test_hands_the_title_back_to_the_model_when_none_was_given(self):
        prompt = format_prompt(template_format="", genre="")

        self.assertIn("The title will be selected by you", prompt)

    def test_hands_the_audience_back_to_the_model_when_none_was_given(self):
        prompt = format_prompt(template_format="", genre="")

        self.assertIn("Select an appropriate target audience", prompt)

    def test_video_drafts_include_action_and_camera_guidance_with_selected_style(self):
        prompt = format_scene_draft("A cat", video=True, style="watercolor")
        self.assertIn("camera move", prompt)
        self.assertIn("one achievable action", prompt)
        self.assertIn("watercolor", prompt)
        self.assertNotIn("short live-action shot", prompt)

    def test_silent_tiktok_script_does_not_request_spoken_lines(self):
        prompt = format_prompt("", "", narration=False, platform="TIKTOK", scene_count=3)
        self.assertIn("Omit all sentence narration fields", prompt)
        self.assertNotIn("Each spoken entry", prompt)
        self.assertNotIn("Open the narration", prompt)
        self.assertNotIn("call to action", prompt)

    def test_web_ignores_generation_style_and_video_instructions(self):
        prompt = format_scene_draft("Paris", video=True, image_mode="WEB", style="oil paint")
        self.assertIn("self-contained", prompt)
        self.assertIn("English search terms", prompt)
        self.assertNotIn("Selected visual style", prompt)
        self.assertNotIn("one achievable action", prompt)

    def test_generation_context_and_language_are_explicit(self):
        prompt = format_prompt("", "", video=True, style="animation")
        self.assertIn("animation", prompt)
        self.assertIn("language explicitly requested", prompt)
        self.assertIn("intentional changes", prompt)

    def test_scene_image_title_is_context_and_not_lettering(self):
        prompt = format_image_prompt("Cats", "a cat")
        self.assertIn("Video context only", prompt)
        self.assertIn("Do not render the video title", prompt)


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
        prompt = format_sora_prompt(image_description=" a cat naps")

        self.assertEqual(prompt, "Cinematic video shot: a cat naps.")

    def test_names_the_video_when_there_is_a_title(self):
        prompt = format_sora_prompt(image_description="a cat naps", title="Cats")

        self.assertIn("Shot from the video titled 'Cats'.", prompt)

    def test_includes_the_style_in_the_description(self):
        prompt = format_sora_prompt(
            image_description="a cat naps", style="warm film grain"
        )

        self.assertIn("rendered in a warm film grain visual style", prompt)

    def test_omits_an_empty_title_rather_than_sending_a_stray_label(self):
        prompt = format_sora_prompt(image_description="a cat naps", title="")

        self.assertNotIn("titled", prompt)


class OtherPromptTests(SimpleTestCase):
    def test_image_prompt_labels_the_title_and_description(self):
        prompt = format_image_prompt(title="Cats", image_description="a cat naps")

        self.assertIn("Title : Cats", prompt)
        self.assertIn("Image Description:a cat naps", prompt)

    def test_update_form_asks_for_a_rewrite_of_the_same_length(self):
        prompt = format_update_form("the old line", "make it funnier")

        self.assertIn("the old line", prompt)
        self.assertIn("make it funnier", prompt)
        self.assertIn("around the same length", prompt)


class CoverPromptTests(SimpleTestCase):
    def test_cover_keeps_exact_title_and_unicode_context_separate_from_direction(self):
        title = 'A "quoted" title — Ελληνικά'
        content = {"title": "Video", "content": ["First scene", "Δεύτερη σκηνή"]}
        prompt = format_cover_prompt(content, title, "Warm lighting")
        self.assertIn(json.dumps(title, ensure_ascii=False), prompt)
        self.assertIn(json.dumps(content, ensure_ascii=False), prompt)
        self.assertTrue(prompt.endswith("Visual direction: Warm lighting"))

    def test_large_context_does_not_truncate_title_or_visual_direction(self):
        prompt = format_cover_prompt(
            {"content": "x" * 20000}, "My title", "Keep the atlas style"
        )
        self.assertIn('Title: "My title"', prompt)
        self.assertTrue(prompt.endswith("Visual direction: Keep the atlas style"))
        self.assertNotIn("x" * 18001, prompt)

    def test_reference_guidance_is_only_added_when_requested(self):
        plain = format_image_prompt("Video", "Atlas", style="watercolor")
        anchored = format_image_prompt(
            "Video", "Atlas", style="watercolor", preserve_reference=True
        )
        self.assertIn("Style: watercolor", plain)
        self.assertNotIn("Preserve recurring characters", plain)
        self.assertIn("Preserve recurring characters", anchored)
