from django.test import SimpleTestCase

from apps.series.signals import episode_video_saved
from apps.videomanagement.domain_signals import storyboard_generated
from apps.videomanagement.models import Video


class StandaloneVideoSignalTests(SimpleTestCase):
    def test_standalone_storyboards_do_not_query_or_change_series_metadata(self):
        for settings in (None, {}, {"creation_mode": "MANUAL"}):
            with self.subTest(settings=settings):
                video = Video(settings=settings)
                storyboard_generated.send(
                    sender=Video, video=video, storyboard={}, new_script=True
                )
                self.assertEqual(video.settings, settings)

    def test_standalone_completion_does_not_query_series(self):
        for status in ("READY", "COMPLETED"):
            for settings in (None, {}, {"creation_mode": "MANUAL"}):
                with self.subTest(status=status, settings=settings):
                    episode_video_saved(
                        sender=Video,
                        instance=Video(status=status, settings=settings),
                        using="default",
                    )
