import json
import math
import re
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.common.youtube import SourceImportError, download_youtube_video
from apps.videomanagement.models import MediaAsset
from apps.videomanagement.services.media.music_discovery import TARGETS
from apps.videomanagement.services.scenes.audio import playable_voiceover
from apps.videomanagement.utils.file_utils import stored_file_exists
from apps.videomanagement.utils.timing import file_timing


class Command(BaseCommand):
    help = "Seed general music from the bundled catalog and download missing audio using pytubefix."

    def add_arguments(self, parser):
        parser.add_argument(
            "--catalog",
            type=Path,
            default=settings.BASE_DIR / "fixtures/music_catalog.json",
        )
        parser.add_argument("--metadata-only", action="store_true")
        parser.add_argument(
            "--best-effort",
            action="store_true",
            help="Keep deployment running if YouTube downloads fail.",
        )

    def handle(self, **options):
        try:
            manifest = json.loads(options["catalog"].read_text())
            if manifest.get("schema_version") != 1 or not isinstance(
                manifest.get("tracks"), list
            ):
                raise ValueError("Expected a version 1 catalog with a tracks list.")
            seen = set()
            for track in manifest["tracks"]:
                key = track["youtube_id"]
                if (
                    not isinstance(key, str)
                    or not re.fullmatch(r"[A-Za-z0-9_-]{11}", key)
                    or key in seen
                ):
                    raise ValueError("Catalog IDs must be distinct YouTube video IDs.")
                seen.add(key)
                if (
                    track["category"] not in TARGETS
                    or track["declared_license"] != "creativeCommon"
                ):
                    raise ValueError(
                        "Every entry needs a supported category and Creative Commons declaration."
                    )
                if not isinstance(track["title"], str) or not track["title"].strip():
                    raise ValueError("Every entry needs a title.")
                duration = track["duration"]
                if (
                    not isinstance(duration, (int, float))
                    or not math.isfinite(duration)
                    or not 0 < duration <= 900
                ):
                    raise ValueError(
                        "Track durations must be between 0 and 900 seconds."
                    )
                tags = track["tags"]
                if (
                    not isinstance(tags, list)
                    or len(tags) > 12
                    or any(
                        not isinstance(tag, str) or not 1 <= len(tag) <= 30
                        for tag in tags
                    )
                ):
                    raise ValueError(
                        "Use up to 12 text tags, each 1–30 characters long."
                    )
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            raise CommandError(f"Invalid music catalog: {exc}") from None

        assets = []
        with transaction.atomic():
            for track in manifest["tracks"]:
                asset, _ = MediaAsset.objects.get_or_create(
                    catalog_source_id=f"youtube:{track['youtube_id']}",
                    defaults={
                        "is_shared": True,
                        "kind": MediaAsset.Kind.AUDIO,
                        "title": track["title"][:100],
                        "tags": track["tags"],
                        "duration": track["duration"],
                        "source_url": f"https://www.youtube.com/watch?v={track['youtube_id']}",
                        "catalog_metadata": track,
                    },
                )
                if (
                    not asset.is_shared
                    or asset.created_by_id
                    or asset.kind != MediaAsset.Kind.AUDIO
                ):
                    raise CommandError(
                        "A catalog source ID belongs to a private or non-audio item."
                    )
                assets.append(asset)
        self.stdout.write(f"Catalog metadata ready: {len(assets)} tracks.")
        if options["metadata_only"]:
            return

        downloaded = skipped = failures = consecutive_failures = 0
        for asset in assets:
            if stored_file_exists(asset.file):
                skipped += 1
                continue
            saved = None
            try:
                with tempfile.TemporaryDirectory() as directory:
                    url = f"https://www.youtube.com/watch?v={asset.catalog_metadata['youtube_id']}"
                    path, _ = download_youtube_video(url, directory, audio_only=True)
                    if path.stat().st_size > 50 * 1024 * 1024:
                        raise SourceImportError("Audio exceeds 50 MB.")
                    with (
                        path.open("rb") as source,
                        playable_voiceover(File(source, name=path.name)) as audio,
                    ):
                        with transaction.atomic():
                            asset = MediaAsset.objects.select_for_update().get(
                                pk=asset.pk
                            )
                            if stored_file_exists(asset.file):
                                skipped += 1
                                continue
                            asset.file.save(audio.name, audio, save=False)
                            saved = asset.file
                            asset.duration = file_timing(asset.file).get(
                                "audio_duration"
                            )
                            asset.save(update_fields=["file", "duration"])
                downloaded += 1
                consecutive_failures = 0
                self.stdout.write(f"Downloaded {asset.title}")
            except Exception as exc:
                if saved:
                    saved.storage.delete(saved.name)
                failures += 1
                consecutive_failures += 1
                self.stderr.write(
                    f"Could not download {asset.catalog_source_id}: {type(exc).__name__}"
                )
                if consecutive_failures >= 3:
                    self.stderr.write(
                        "Paused downloads after three consecutive failures; rerun to retry missing tracks."
                    )
                    break
        self.stdout.write(
            f"Downloaded: {downloaded}; already available: {skipped}; failed: {failures}."
        )
        self.stdout.write(
            "New tracks remain pending license review before appearing as general music."
        )
        if failures and not options["best_effort"]:
            raise CommandError(
                "Some music downloads failed. Saved audio is retained; rerun to retry."
            )
