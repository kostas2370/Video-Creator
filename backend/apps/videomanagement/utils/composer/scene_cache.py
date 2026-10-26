"""Private, bounded storage for reusable lossless scene visuals."""

import hashlib
import json
import logging
import os
import shutil
import tempfile
import time
from pathlib import Path

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation

from ..motion import resolved_motion

logger = logging.getLogger(__name__)
# Bump when the intermediate scene filters or encoding settings change.
CACHE_VERSION = 1


def file_identity(path, *, contents=False):
    if not path:
        return None
    path = Path(path).resolve()
    try:
        stat = path.stat()
        identity = [
            str(path),
            stat.st_size,
            stat.st_mtime_ns,
            stat.st_ctime_ns,
            stat.st_ino,
        ]
        if contents:
            # A same-size replacement can retain timestamps on coarse filesystems.
            # Stream the source hash to keep memory independent of file size.
            with path.open("rb") as source:
                identity.append(hashlib.file_digest(source, "sha256").hexdigest())
        return identity
    except OSError:
        return [str(path), "missing"]


class SourceFingerprints:
    """Snapshot source identities for one export; never reuse across exports."""

    def __init__(self):
        self.identities = {}

    def identity(self, path):
        path = Path(path).resolve()
        if path not in self.identities:
            self.identities[path] = file_identity(path, contents=True)
        return self.identities[path]


def link_or_copy(source, destination):
    try:
        os.link(source, destination)
    except OSError:
        shutil.copyfile(source, destination)


def remove_project_cache(video_id):
    root = Path(settings.FFMPEG_SCENE_CACHE_ROOT).resolve()
    if root.is_relative_to(Path(settings.MEDIA_ROOT).resolve()):
        return
    directory = root / hashlib.sha256(str(video_id).encode()).hexdigest()
    try:
        shutil.rmtree(directory)
    except FileNotFoundError:
        pass
    except OSError:
        logger.warning("Could not remove a project's scene cache", exc_info=True)


class SceneClipCache:
    def __init__(self, video_id):
        self.root = Path(settings.FFMPEG_SCENE_CACHE_ROOT).resolve()
        self.directory = self.root / hashlib.sha256(str(video_id).encode()).hexdigest()
        self.max_bytes = settings.FFMPEG_SCENE_CACHE_BYTES
        self.ttl = settings.FFMPEG_SCENE_CACHE_TTL
        self.enabled = self.max_bytes > 0 and self.ttl > 0
        # The cache must never be served as user media.
        if self.root.is_relative_to(Path(settings.MEDIA_ROOT).resolve()):
            self.enabled = False
            logger.warning("Scene cache disabled: its directory is inside MEDIA_ROOT")
        self.encoder = file_identity(shutil.which("ffmpeg"))
        if self.enabled:
            self.prune()

    def key(self, segment, size, fps, previous=None, *, sources=None):
        field = segment.image.file if segment.image else None
        try:
            source = (
                (
                    sources.identity(field.path)
                    if sources is not None
                    else file_identity(field.path, contents=True)
                )
                if field
                else None
            )
        except (ValueError, SuspiciousFileOperation):
            source = None
        value = {
            "version": CACHE_VERSION,
            "encoder": self.encoder,
            "source": source,
            "size": size,
            "fps": fps,
            "type": segment.visual_type,
            "duration": segment.duration,
            "base_duration": segment.base_duration,
            "loop": segment.loop_visual,
            "trim_start": segment.trim_start,
            "shots": [
                self.key(shot, size, fps, sources=sources) for shot in segment.shots
            ],
            "motion": resolved_motion(segment.content),
            "intensity": segment.content.motion_intensity,
            "fade_in": segment.fade_in,
            "fade_out": segment.fade_out,
            "dissolve_in": segment.dissolve_in,
            "previous": previous if segment.dissolve_in else None,
        }
        return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()

    def stage(self, key, destination):
        """Pin a hit in the render directory so eviction cannot interrupt FFmpeg."""
        if not self.enabled:
            return False
        clip = self.directory / f"{key}.mkv"
        try:
            size = json.loads(clip.with_suffix(".json").read_text())["bytes"]
            stat = clip.stat()
            if (
                size <= 0
                or stat.st_size != size
                or time.time() - stat.st_mtime > self.ttl
            ):
                return False
            link_or_copy(clip, destination)
            if destination.stat().st_size != size:
                destination.unlink(missing_ok=True)
                return False
            os.utime(clip, None)
            return True
        except (OSError, ValueError, KeyError, TypeError):
            destination.unlink(missing_ok=True)
            return False

    def store(self, key, source):
        if not self.enabled:
            return
        try:
            size = source.stat().st_size
            if size <= 0 or size > self.max_bytes:
                return
            self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            with tempfile.TemporaryDirectory(
                prefix=".write-", dir=self.directory
            ) as temporary:
                clip = Path(temporary, f"{key}.mkv")
                metadata = clip.with_suffix(".json")
                link_or_copy(source, clip)
                metadata.write_text(json.dumps({"bytes": size}))
                os.replace(clip, self.directory / clip.name)
                os.replace(metadata, self.directory / metadata.name)
            self.prune()
        except OSError:
            # An unwritable/full cache must not fail an otherwise valid export.
            logger.warning("Could not store a reusable scene clip", exc_info=True)

    def prune(self):
        """Evict expired and least-recently-used clips across all projects."""
        try:
            now = time.time()
            # A worker killed while copying a clip may leave an unfinished write.
            for temporary in self.root.glob("*/.write-*"):
                try:
                    if now - temporary.stat().st_mtime > self.ttl:
                        shutil.rmtree(temporary)
                except OSError:
                    continue
            entries = []
            for clip in self.root.glob("*/*.mkv"):
                try:
                    stat = clip.stat()
                    metadata = clip.with_suffix(".json")
                    size = stat.st_size + (
                        metadata.stat().st_size if metadata.exists() else 0
                    )
                    entries.append((stat.st_mtime, size, clip))
                except OSError:
                    continue
            total = sum(size for _, size, _ in entries)
            for modified, size, clip in sorted(entries):
                if now - modified <= self.ttl and total <= self.max_bytes:
                    continue
                try:
                    clip.unlink(missing_ok=True)
                    clip.with_suffix(".json").unlink(missing_ok=True)
                    total -= size
                    clip.parent.rmdir()
                except OSError:
                    continue
        except OSError:
            logger.warning("Could not prune reusable scene clips", exc_info=True)
