import os
import tempfile
import time
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from django.db import transaction
from django.test import SimpleTestCase, TestCase, override_settings

from ...baker_recipes import video
from ...utils.composer.render import can_render_directly
from ...utils.composer.scene_cache import SceneClipCache


class SceneClipCacheTests(SimpleTestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.enterContext(
            override_settings(
                MEDIA_ROOT=self.root / "media",
                FFMPEG_SCENE_CACHE_ROOT=self.root / "private-cache",
                FFMPEG_SCENE_CACHE_BYTES=1024,
                FFMPEG_SCENE_CACHE_TTL=60,
                FFMPEG_DIRECT_RENDER=True,
            )
        )
        self.source = self.root / "source.png"
        self.source.write_bytes(b"original pixels")
        self.segment = SimpleNamespace(
            image=SimpleNamespace(file=SimpleNamespace(path=self.source)),
            content=SimpleNamespace(
                pk=uuid4(), motion_style="PAN_RIGHT", motion_intensity="SUBTLE"
            ),
            visual_type="image",
            duration=2,
            base_duration=2,
            loop_visual=False,
            fade_in=0,
            fade_out=0,
            dissolve_in=0,
        )
        self.cache = SceneClipCache(uuid4())

    def key(self, segment=None, size=(160, 90), previous=None):
        return self.cache.key(segment or self.segment, size, 24, previous)

    def store(self, key="clip", data=b"lossless scene"):
        source = self.root / f"{key}.mkv"
        source.write_bytes(data)
        self.cache.store(key, source)
        return source

    def test_hits_are_pinned_even_if_cache_is_evicted(self):
        self.store()
        destination = self.root / "render-scene.mkv"
        self.assertTrue(self.cache.stage("clip", destination))
        self.cache.max_bytes = 0
        self.cache.prune()
        self.assertFalse(list(self.cache.root.glob("*/*.mkv")))
        self.assertEqual(destination.read_bytes(), b"lossless scene")

    def test_cache_is_scoped_to_the_project(self):
        self.store()
        other = SceneClipCache(uuid4())
        self.assertFalse(other.stage("clip", self.root / "other-scene.mkv"))

    def test_visual_settings_and_render_dimensions_invalidate_clips(self):
        original = self.key()
        for field, value in {
            "duration": 3,
            "base_duration": 1,
            "loop_visual": True,
            "fade_in": 0.2,
            "fade_out": 0.2,
            "dissolve_in": 0.2,
            "visual_type": "video",
        }.items():
            with self.subTest(field=field):
                changed = deepcopy(self.segment)
                setattr(changed, field, value)
                self.assertNotEqual(original, self.key(changed))
        for field, value in (
            ("motion_style", "PAN_LEFT"),
            ("motion_intensity", "STRONG"),
        ):
            changed = deepcopy(self.segment)
            setattr(changed.content, field, value)
            self.assertNotEqual(original, self.key(changed))
        self.assertNotEqual(original, self.key(size=(90, 160)))

    def test_replacement_is_detected_even_with_the_same_file_size_and_mtime(self):
        original, stat = self.key(), self.source.stat()
        self.source.write_bytes(b"replaced pixels")
        os.utime(self.source, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        self.assertNotEqual(original, self.key())

    def test_dissolves_depend_on_the_previous_clip_but_cuts_do_not(self):
        self.assertEqual(self.key(previous="before"), self.key(previous="after"))
        self.segment.dissolve_in = 0.3
        self.assertNotEqual(self.key(previous="before"), self.key(previous="after"))

    def test_final_caption_overlay_and_audio_changes_do_not_invalidate_visuals(self):
        original = self.key()
        self.segment.content.text = "New captions"
        self.segment.content.overlays = [{"text": "New overlay"}]
        self.segment.content.audio_settings = {"volume": 0.5}
        self.assertEqual(original, self.key())

    def test_expired_and_truncated_entries_are_misses(self):
        self.store()
        clip = self.cache.directory / "clip.mkv"
        old = time.time() - 120
        os.utime(clip, (old, old))
        self.assertFalse(self.cache.stage("clip", self.root / "expired.mkv"))
        self.cache.prune()
        self.assertFalse(clip.exists())
        self.store()
        clip.write_bytes(b"truncated")
        self.assertFalse(self.cache.stage("clip", self.root / "truncated.mkv"))

    def test_lru_eviction_respects_the_global_budget(self):
        self.cache.max_bytes = 50
        self.store("older", b"x" * 20)
        clip = self.cache.directory / "older.mkv"
        old = time.time() - 10
        os.utime(clip, (old, old))
        self.store("newer", b"y" * 20)
        self.assertFalse(clip.exists())
        self.assertTrue((self.cache.directory / "newer.mkv").exists())
        self.assertLessEqual(
            sum(p.stat().st_size for p in self.cache.root.glob("*/*") if p.is_file()),
            50,
        )

    def test_unwritable_cache_does_not_prevent_rendering(self):
        self.cache.root.write_bytes(b"not a directory")
        with self.assertLogs(
            "apps.videomanagement.utils.composer.scene_cache", level="WARNING"
        ):
            self.store()
        self.assertFalse(self.cache.stage("clip", self.root / "miss.mkv"))

    def test_cache_is_disabled_if_it_would_be_exposed_under_media_root(self):
        with override_settings(FFMPEG_SCENE_CACHE_ROOT=self.root / "media" / "cache"):
            with self.assertLogs(
                "apps.videomanagement.utils.composer.scene_cache", level="WARNING"
            ):
                cache = SceneClipCache(uuid4())
        self.assertFalse(cache.enabled)

    def test_direct_path_is_bounded_and_preserves_dissolve_fallback(self):
        self.assertTrue(can_render_directly([self.segment]))
        self.assertFalse(can_render_directly([self.segment] * 2))
        self.segment.content.motion_style = "NONE"
        self.assertTrue(can_render_directly([self.segment] * 3))
        self.assertFalse(can_render_directly([self.segment] * 4))
        self.segment.dissolve_in = 0.2
        self.assertFalse(can_render_directly([self.segment]))
        with override_settings(FFMPEG_DIRECT_RENDER=False):
            self.segment.dissolve_in = 0
            self.assertFalse(can_render_directly([self.segment]))


class ProjectCacheDeletionTests(TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.enterContext(
            override_settings(
                MEDIA_ROOT=self.root / "media",
                FFMPEG_SCENE_CACHE_ROOT=self.root / "cache",
            )
        )
        self.enterContext(patch("apps.videomanagement.signals.publish_update"))
        self.video = video.make()
        self.cache = SceneClipCache(self.video.pk)
        source = self.root / "scene.mkv"
        source.write_bytes(b"valid cached scene")
        self.cache.store("clip", source)

    def test_project_cache_is_removed_after_the_delete_commits(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.video.delete()
            self.assertTrue(self.cache.directory.exists())
        self.assertFalse(self.cache.directory.exists())

    def test_rolled_back_delete_preserves_reusable_clips(self):
        with self.captureOnCommitCallbacks(execute=True):
            with self.assertRaises(ValueError):
                with transaction.atomic():
                    self.video.delete()
                    raise ValueError("rollback")
        self.assertTrue(self.cache.directory.exists())
