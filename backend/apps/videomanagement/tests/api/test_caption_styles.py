from dataclasses import replace
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from django.urls import reverse

from ...services.caption_styles import CAPTION_STYLES, video_caption_style, resolve_style
from ...services.subtitles import CaptionCue, scene_cues, word_cues
from ...utils.composer.captions import ASS_STYLE_FIELDS, ass_header, caption_ass_text, write_captions
from .base import ApiTestCase


class CustomCaptionStyleTests(ApiTestCase):
    def test_user_style_round_trips_and_reaches_preview_and_scene_editor(self):
        video = self.video_for(settings={"subtitles": True})
        config = {"name": "My green captions", "font": "DejaVu Serif", "font_size": 7,
                  "color": "#aaffff", "highlight_color": "#00ff00", "position": "top",
                  "uppercase": False, "bold": False, "max_words": 2}
        response = self.client.patch(reverse("video-detail", args=[video.pk]),
                                     {"caption_style": "CUSTOM", "caption_config": config}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        video.refresh_from_db()
        self.assertEqual(video.settings["caption_config"], config)
        resolved = video_caption_style(video)
        self.assertEqual((resolved.color, resolved.max_words), ("#aaffff", 2))
        catalog = self.client.get(reverse("video-caption-styles"))
        self.assertEqual(catalog.status_code, 200)
        self.assertEqual(set(catalog.data["presets"]), set(CAPTION_STYLES))
        self.assertIn(config["font"], catalog.data["fonts"])
        from ...baker_recipes import scene
        item = scene.make(video=video, text="One two three four")
        cues = scene_cues(item, duration=4, highlight=True)
        self.assertTrue(all(len(cue.text.split()) <= 2 for cue in cues))
        from ...serializers.preview import PreviewTimelineSerializer
        with patch("apps.videomanagement.services.preview.scene_segment") as segment, patch(
            "apps.videomanagement.serializers.preview.voice_tracks", return_value=[]
        ):
            segment.return_value = SimpleNamespace(kind="scene", content=item, narration_duration=4,
                duration=4, start=0, base_duration=4, image=None, index=1, visual_duration=None,
                visual_type="image", loop_visual=False, clip_audio=False, transition="CUT", transition_duration=None,
                fade_in=0, fade_out=0, dissolve_in=0)
            data = PreviewTimelineSerializer(video).data
        self.assertEqual(data["caption_config"], resolved.to_dict())

    def test_invalid_styles_and_raw_renderer_options_are_rejected(self):
        video = self.video_for()
        invalid = [{"font": "/tmp/font.ttf"}, {"color": "red"}, {"font_size": 100},
                   {"max_words": 0}, {"position": "outside"}, {"ass_tags": r"\pos(0,0)"},
                   {"scale_with_frame": False}, {"shadow": float("inf")}]
        for config in invalid:
            with self.subTest(config=config):
                # Infinity is tested directly because JSON intentionally disallows it.
                if "shadow" in config:
                    from ...serializers.caption_styles import CaptionStyleSerializer
                    self.assertFalse(CaptionStyleSerializer(data=config).is_valid())
                    continue
                response = self.client.patch(reverse("video-detail", args=[video.pk]),
                    {"caption_style": "CUSTOM", "caption_config": config}, format="json")
                self.assertEqual(response.status_code, 400, response.data)
        video.refresh_from_db()
        self.assertNotIn("caption_config", video.settings)


class CaptionStyleRenderingTests(SimpleTestCase):
    def test_named_ass_fields_use_resolved_layout_and_colors(self):
        style = resolve_style("CUSTOM", {"font_size": 7, "color": "#aaffff", "highlight_color": "#00ff00",
                                        "outline_color": "#113355", "position": "top", "margin_vertical": 11})
        header = ass_header(style, (1080, 1920))
        line = next(line for line in header.splitlines() if line.startswith("Style:"))
        values = dict(zip(ASS_STYLE_FIELDS, line.removeprefix("Style: ").split(",")))
        self.assertEqual(values["Fontsize"], "75.6")
        self.assertEqual(values["PrimaryColour"], "&H00FFFFAA&")
        self.assertEqual(values["OutlineColour"], "&H00553311&")
        self.assertEqual((values["Alignment"], values["MarginV"]), ("8", "211"))
        text = caption_ass_text(CaptionCue(0, 1, "Hello world", 1), style=replace(style, uppercase=False))
        self.assertEqual(text, "Hello {\\1c&H0000FF00&}world{\\1c&H00FFFFAA&}")

    def test_new_registry_preset_needs_no_renderer_or_grouping_branch(self):
        style = replace(resolve_style("TIKTOK"), name="Quiet", uppercase=False, bold=False,
                        highlight_words=False, max_words=1, color="#aaffff", position="middle")
        with patch.dict(CAPTION_STYLES, {"QUIET": style}):
            video = SimpleNamespace(settings={"caption_style": "QUIET"})
            scene = SimpleNamespace(pk="scene", video=video, text="Hello world", audio_settings={})
            segment = SimpleNamespace(content=scene, start=0, narration_duration=2)
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory, "captions.ass")
                write_captions(path, [segment], (1080, 1920))
                result = path.read_text()
            self.assertEqual(result.count("Dialogue:"), 2)
            self.assertIn(",,Hello", result)
            self.assertNotIn("{\\1c", result)
            self.assertIn(",5,86,151,0,1", result)

    def test_large_custom_text_scales_inside_the_selected_margins(self):
        style = resolve_style("CUSTOM", {"font_size": 15})
        self.assertAlmostEqual(style.text_scale("a" * 20, (1080, 1920)), 78 / 180)
        self.assertEqual(style.text_scale("Hi", (1080, 1920)), 1)

    def test_custom_grouping_and_highlight_are_independent_of_uppercase(self):
        words = [{"text": "Hello", "start": 0, "end": 0.5}, {"text": "world", "start": 0.5, "end": 1}]
        style = resolve_style("CUSTOM", {"max_words": 1, "uppercase": False})
        cues = word_cues(words, style, highlight=True)
        self.assertEqual([cue.text for cue in cues], ["Hello", "world"])
        self.assertTrue(all(cue.active_word == 0 for cue in cues))
        self.assertEqual(caption_ass_text(cues[0], style=replace(style, highlight_words=False)), "Hello")
