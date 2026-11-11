import json
import math
import re
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.common.youtube import SourceImportError, download_youtube_video
from apps.videomanagement.models import MusicCatalogTrack
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
            "--approve-only",
            action="store_true",
            help="Approve already-downloaded Creative Commons tracks without downloading more files.",
        )
        parser.add_argument(
            "--no-auto-approve",
            action="store_true",
            help="Keep downloaded tracks pending manual approval.",
        )
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
            for entry in manifest["tracks"]:
                key = entry["youtube_id"]
                if (
                    not isinstance(key, str)
                    or not re.fullmatch(r"[A-Za-z0-9_-]{11}", key)
                    or key in seen
                ):
                    raise ValueError("Catalog IDs must be distinct YouTube video IDs.")
                seen.add(key)
                if (
                    entry["category"] not in TARGETS
                    or entry["declared_license"] != "creativeCommon"
                ):
                    raise ValueError(
                        "Every entry needs a supported category and Creative Commons declaration."
                    )
                if not isinstance(entry["title"], str) or not entry["title"].strip():
                    raise ValueError("Every entry needs a title.")
                duration = entry["duration"]
                if (
                    not isinstance(duration, (int, float))
                    or not math.isfinite(duration)
                    or not 0 < duration <= 900
                ):
                    raise ValueError(
                        "Track durations must be between 0 and 900 seconds."
                    )
                tags = entry["tags"]
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

        tracks = []
        with transaction.atomic():
            for entry in manifest["tracks"]:
                track, _ = MusicCatalogTrack.objects.get_or_create(
                    source_id=f"youtube:{entry['youtube_id']}",
                    defaults={
                        "category": entry["category"],
                        "title": entry["title"][:100],
                        "tags": entry["tags"],
                        "duration": entry["duration"],
                        "source_url": f"https://www.youtube.com/watch?v={entry['youtube_id']}",
                        "metadata": entry,
                    },
                )
                tracks.append(track)
        self.stdout.write(f"Catalog metadata ready: {len(tracks)} tracks.")
        if options["metadata_only"]:
            return

        downloaded = skipped = failures = consecutive_failures = 0
        for track in [] if options["approve_only"] else tracks:
            if stored_file_exists(track.file):
                skipped += 1
                continue
            saved = None
            try:
                with tempfile.TemporaryDirectory() as directory:
                    url = f"https://www.youtube.com/watch?v={track.metadata['youtube_id']}"
                    path, _ = download_youtube_video(url, directory, audio_only=True)
                    if path.stat().st_size > 50 * 1024 * 1024:
                        raise SourceImportError("Audio exceeds 50 MB.")
                    with (
                        path.open("rb") as source,
                        playable_voiceover(File(source, name=path.name)) as audio,
                    ):
                        with transaction.atomic():
                            track = MusicCatalogTrack.objects.select_for_update().get(
                                pk=track.pk
                            )
                            if stored_file_exists(track.file):
                                skipped += 1
                                continue
                            track.file.save(audio.name, audio, save=False)
                            saved = track.file
                            track.duration = file_timing(track.file).get(
                                "audio_duration"
                            )
                            track.save(update_fields=["file", "duration"])
                downloaded += 1
                consecutive_failures = 0
                self.stdout.write(f"Downloaded {track.title}")
            except Exception as exc:
                if saved:
                    saved.storage.delete(saved.name)
                failures += 1
                consecutive_failures += 1
                self.stderr.write(
                    f"Could not download {track.source_id}: {type(exc).__name__}"
                )
                if consecutive_failures >= 3:
                    self.stderr.write(
                        "Paused downloads after three consecutive failures; rerun to retry missing tracks."
                    )
                    break
        self.stdout.write(
            f"Downloaded: {downloaded}; already available: {skipped}; failed: {failures}."
        )
        approved = 0
        if not options["no_auto_approve"]:
            for track in MusicCatalogTrack.objects.filter(
                pk__in=[item.pk for item in tracks], approved=False
            ):
                metadata = track.metadata or {}
                if metadata.get(
                    "declared_license"
                ) != "creativeCommon" or not stored_file_exists(track.file):
                    continue
                track.license_url = (
                    track.license_url
                    or "https://support.google.com/youtube/answer/2797468"
                )
                uploader = metadata.get("channel_title") or metadata.get("channel_id")
                if not uploader:
                    continue
                track.attribution = track.attribution or (
                    f'"{track.title}" — uploaded by {uploader}. '
                    f"{track.source_url}. Declared Creative Commons Attribution (CC BY) on YouTube. "
                    f"License information: {track.license_url}. Audio extracted for background music; edits may include trimming and fades."
                )
                track.metadata = {
                    **metadata,
                    "approval_basis": "youtube_declared_creative_commons",
                    "approved_at": timezone.now().isoformat(),
                }
                track.approved = True
                track.save(
                    update_fields=["approved", "license_url", "attribution", "metadata"]
                )
                approved += 1
        self.stdout.write(
            f"Automatically approved: {approved}. Approval uses the stored YouTube Creative Commons declaration."
        )
        if failures and not options["best_effort"]:
            raise CommandError(
                "Some music downloads failed. Saved audio is retained; rerun to retry."
            )
