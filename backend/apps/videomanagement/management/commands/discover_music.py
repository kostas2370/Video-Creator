import os
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.videomanagement.services.media.music_discovery import (
    TARGETS,
    DiscoveryError,
    YouTubeClient,
    discover,
    export_catalog,
)


class Command(BaseCommand):
    help = "Discover 390 Creative Commons music candidates for the shared catalog."

    def add_arguments(self, parser):
        parser.add_argument(
            "--export",
            type=Path,
            help="Write a portable catalog JSON snapshot after discovery.",
        )
        parser.add_argument("--category", choices=TARGETS, action="append")
        parser.add_argument("--pages-per-query", type=int, default=3)
        parser.add_argument("--min-seconds", type=int, default=30)
        parser.add_argument("--max-seconds", type=int, default=900)

    def handle(self, **options):
        key = os.environ.get("YOUTUBE_API_KEY", "").strip()
        if not key:
            raise CommandError("Set YOUTUBE_API_KEY to a YouTube Data API v3 key.")
        if (
            options["pages_per_query"] < 1
            or options["min_seconds"] < 1
            or options["max_seconds"] < options["min_seconds"]
        ):
            raise CommandError(
                "Use positive limits with maximum duration at least equal to minimum."
            )
        categories = list(dict.fromkeys(options["category"] or TARGETS))
        try:
            counts = discover(
                YouTubeClient(key),
                categories,
                pages_per_query=options["pages_per_query"],
                minimum=options["min_seconds"],
                maximum=options["max_seconds"],
                report=self.stdout.write,
            )
        except DiscoveryError as exc:
            raise CommandError(str(exc)) from None
        self.stdout.write(
            "Candidates saved for review. No audio downloaded or published."
        )
        if options["export"]:
            count = export_catalog(options["export"])
            self.stdout.write(f"Exported {count} entries to {options['export']}.")
        if any(counts[category] < TARGETS[category] for category in categories):
            raise CommandError(
                "Some categories are below target. Rerun with a larger --pages-per-query limit; saved candidates are retained."
            )
