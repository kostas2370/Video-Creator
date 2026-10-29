from django.test import SimpleTestCase

from apps.videomanagement.hooks import run_video_hooks
from apps.videomanagement.models import Video


class StandaloneVideoHookTests(SimpleTestCase):
    def test_standalone_storyboards_do_not_query_or_change_series_metadata(self):
        for settings in (None, {}, {"creation_mode": "MANUAL"}):
            with self.subTest(settings=settings):
                video = Video(settings=settings)
                run_video_hooks(
                    "storyboard_generated", video=video, storyboard={}, new_script=True
                )
                self.assertEqual(video.settings, settings)

    def test_standalone_completion_does_not_query_series(self):
        for status in ("READY", "COMPLETED"):
            for settings in (None, {}, {"creation_mode": "MANUAL"}):
                with self.subTest(status=status, settings=settings):
                    run_video_hooks(
                        "video_saved", video=Video(status=status, settings=settings)
                    )
