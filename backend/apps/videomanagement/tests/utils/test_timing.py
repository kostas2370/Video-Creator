import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from django.core.cache import cache
from django.test import SimpleTestCase, override_settings

from ...utils.timing import media_timing, scene_timing


class MediaTimingTests(SimpleTestCase):
    def test_probe_is_cached_and_refreshes_when_the_file_changes(self):
        cache.clear()
        with TemporaryDirectory() as directory:
            path = Path(directory, 'audio.wav')
            path.write_bytes(b'audio')
            result = SimpleNamespace(stdout=json.dumps({'format': {'duration': '4'}, 'streams': [{'codec_type': 'audio', 'duration': 'N/A'}]}))
            with patch('apps.videomanagement.utils.timing.subprocess.run', return_value=result) as probe:
                self.assertEqual(media_timing(path), {'duration': 4, 'audio_duration': 4})
                media_timing(path)
                self.assertEqual(probe.call_count, 1)
                path.write_bytes(b'new audio')
                media_timing(path)
                self.assertEqual(probe.call_count, 2)

    @override_settings(SILENT_SCENE_SECONDS=7)
    def test_narration_and_silent_clip_timing_match_the_render_rules(self):
        image = SimpleNamespace(file=SimpleNamespace(name='clip.mp4'), with_audio=True)
        scene = SimpleNamespace(video=SimpleNamespace(settings={'narration': True}), file=object(), is_last=True, pause_after=0.75)
        with patch('apps.videomanagement.utils.timing.file_timing', side_effect=[{'duration': 4, 'audio_duration': 4}, {'duration': 8, 'audio_duration': 6}]):
            self.assertEqual(scene_timing(scene, image), {'base_duration': 6, 'duration': 6.75})
        scene.video.settings = {'narration': False}
        image.with_audio = False
        with patch('apps.videomanagement.utils.timing.file_timing', return_value={'duration': 8, 'audio_duration': 6}):
            self.assertEqual(scene_timing(scene, image), {'base_duration': 8, 'duration': 8.75})
        self.assertEqual(scene_timing(scene), {'base_duration': 7, 'duration': 7.75})

    def test_existing_ending_hold_is_included(self):
        image = SimpleNamespace(file=None, with_audio=False)
        scene = SimpleNamespace(video=SimpleNamespace(settings={}), file=object(), is_last=True, pause_after=1)
        with patch('apps.videomanagement.utils.timing.file_timing', return_value={'duration': 4, 'audio_duration': 4}), patch('apps.videomanagement.utils.timing.media_timing', return_value={'duration': 1}):
            self.assertEqual(scene_timing(scene, image), {'base_duration': 6, 'duration': 7})
