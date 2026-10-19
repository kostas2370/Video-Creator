from django.test import SimpleTestCase

from ...serializers.overlays import OverlaySerializer
from ...utils.composer.ass import ASS_STYLE_FIELDS, ass_color, style_line
from ...utils.composer.overlays import text_overlay
from ...utils.overlay_text import overlay_font, overlay_text_layout


class OverlayTextLayoutTests(SimpleTestCase):
    def test_wide_glyphs_and_long_text_fit_both_frame_dimensions(self):
        for family in ("DejaVu Sans", "Poppins", "Lato", "Bebas Neue"):
            for frame in ((1920, 1080), (1080, 1920)):
                with self.subTest(family=family, frame=frame):
                    font = overlay_font(family)
                    text, size = overlay_text_layout("W" * 200, 8, family, frame)
                    self.assertEqual(text.replace("\n", ""), "W" * 200)
                    self.assertTrue(all(font.getlength(line) / 1000 * size <= 88 for line in text.splitlines()))
                    self.assertLessEqual(len(text.splitlines()) * size * 1.5, 88 * frame[1] / frame[0])

    def test_short_text_preserves_size_and_deliberate_breaks(self):
        text, size = overlay_text_layout("Name\nRole", 4, "Poppins", (1920, 1080))
        self.assertEqual((text, size), ("Name\nRole", 4))

    def test_style_fields_and_escaping_preserve_opacity_and_placement(self):
        serializer = OverlaySerializer(data={"kind": "title", "text": r"{\pos(0,0)}", "font": "Poppins", "opacity": 0.5, "position": "top-right"})
        serializer.is_valid(raise_exception=True)
        style, event = text_overlay(serializer.validated_data, "Overlay0", (1920, 1080), 0.2, 0.8)
        values = style_line(style).removeprefix("Style: ").split(",")
        fields = dict(zip(ASS_STYLE_FIELDS, values))
        self.assertEqual(len(values), len(ASS_STYLE_FIELDS))
        self.assertEqual(fields["Fontname"], "Poppins")
        self.assertEqual(fields["PrimaryColour"], ass_color("#ffffff", 0.5))
        self.assertEqual(fields["BorderStyle"], "3")
        self.assertEqual(fields["Alignment"], "9")
        self.assertIn(r"{\an9\pos(1824.0,54.0)}", event)
        self.assertIn("｛＼pos(0,0)｝", event)
        self.assertNotIn(r"{\pos(0,0)}", event)
