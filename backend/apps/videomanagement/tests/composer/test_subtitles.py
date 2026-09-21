from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from ...utils.composer import subtitles
from ...utils.composer.subtitles import create_subtitle_clip
from ..doubles import FakeClip


class CreateSubtitleClipTests(SimpleTestCase):
    @override_settings(SUBTITLE_FONT="DejaVu-Sans")
    def test_builds_a_caption_that_lasts_as_long_as_the_line(self):
        clip = FakeClip()

        with patch.object(subtitles, "TextClip", return_value=clip) as text:
            subtitle = create_subtitle_clip("hello", duration=4.0)

        self.assertEqual(subtitle.duration, 4.0)
        self.assertEqual(text.call_args.kwargs["method"], "caption")
        self.assertEqual(text.call_args.kwargs["font"], "DejaVu-Sans")

    def test_returns_none_rather_than_failing_the_render_when_text_cannot_be_drawn(
        self,
    ):
        # ImageMagick is a separate binary and is not always configured.
        with patch.object(subtitles, "TextClip", side_effect=OSError("no convert")):
            self.assertIsNone(create_subtitle_clip("hello", 4.0))
