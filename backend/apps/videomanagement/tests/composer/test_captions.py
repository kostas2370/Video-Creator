import tempfile
from pathlib import Path
from types import SimpleNamespace

from django.test import SimpleTestCase

from ...services.subtitles import CaptionCue
from ...services.caption_styles import resolve_style
from ...utils.composer.captions import caption_ass_text, write_captions


class CaptionRenderTests(SimpleTestCase):
    def test_word_colors_cannot_enable_ass_tags_from_user_text(self):
        cue = CaptionCue(0, 1, r"Hello {\pos(0,0)}" + "\nworld", 2)
        text = caption_ass_text(cue, style=resolve_style("TIKTOK"))
        self.assertIn(r"{\1c&H0046E8FF&}WORLD{\1c&H00FFFFFF&}", text)
        self.assertNotIn(r"{\pos", text)
        self.assertIn(r"\N", text)

    def test_tiktok_export_has_scaled_bold_style_safe_margins_and_word_events(self):
        video = SimpleNamespace(settings={"platform": "TIKTOK"})
        scene = SimpleNamespace(pk="scene", text="One two six ten", video=video, audio_settings={})
        segment = SimpleNamespace(content=scene, start=2, narration_duration=4)
        with tempfile.TemporaryDirectory() as root:
            path = Path(root, "captions.ass")
            write_captions(path, [segment], (1080, 1920))
            text = path.read_text()
        self.assertIn("ScaledBorderAndShadow: yes", text)
        self.assertIn(",64.8,&H00FFFFFF", text)
        self.assertIn(",-1,0,0,0,100,100", text)
        self.assertIn(",86,151,422,1", text)
        self.assertEqual(text.count("Dialogue:"), 4)
        self.assertIn("0:00:02.00,0:00:03.00", text)
        self.assertIn(r"{\1c&H0046E8FF&}ONE", text)
