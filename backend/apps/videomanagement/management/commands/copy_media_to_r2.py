from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from itertools import islice

from django.apps import apps
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.management.base import BaseCommand, CommandError
from django.db.models import FileField

from apps.clips.storage import ClipStorage
from apps.common.media_archive import (
    ArchiveError,
    blob_name,
    copy_verified,
    local_path,
    relative_name,
)
from apps.common.r2_archive import R2Archive
from apps.publishing.storage import PrivateExportStorage


def registered_files():
    """Include soft-deleted records and deduplicate shared file references."""
    seen = set()
    for model in apps.get_models():
        if model._meta.app_label not in {
            "videomanagement",
            "clips",
            "series",
            "publishing",
        }:
            continue
        for field in model._meta.fields:
            if not isinstance(field, FileField):
                continue
            storage = field.storage
            if not isinstance(storage, FileSystemStorage):
                raise CommandError("This copy command requires local source storage.")
            namespace = (
                "clips"
                if isinstance(storage, ClipStorage)
                else "publishing"
                if isinstance(storage, PrivateExportStorage)
                else "media"
            )
            names = (
                model._base_manager.exclude(**{field.name: ""})
                .exclude(**{f"{field.name}__isnull": True})
                .values_list(field.name, flat=True)
                .iterator(chunk_size=500)
            )
            for name in names:
                key = (namespace, name)
                if key not in seen:
                    seen.add(key)
                    yield namespace, storage, name


class Command(BaseCommand):
    help = "Copy registered local media to Cloudflare R2. Dry run unless --execute is supplied."
    destination_label = "Cloudflare R2"

    def get_archive(self):
        return R2Archive(
            settings.R2_ACCOUNT_ID,
            settings.R2_BUCKET_NAME,
            settings.R2_ACCESS_KEY_ID,
            settings.R2_SECRET_ACCESS_KEY,
            settings.R2_JURISDICTION,
        )

    def add_arguments(self, parser):
        parser.add_argument(
            "--execute",
            action="store_true",
            help=f"Upload and verify bytes in {self.destination_label}.",
        )
        parser.add_argument(
            "--workers",
            type=int,
            choices=range(1, 17),
            default=4,
            help="Parallel file transfers (1–16, default 4).",
        )

    def copy_file(self, entry, archive):
        namespace, storage, name = entry
        try:
            name = relative_name(storage, name)
            destination = blob_name(namespace, name)
            path = local_path(storage, name)
            return (
                copy_verified(path, destination, archive) if archive else "ready"
            ), None
        except ArchiveError as exc:
            return "failed", str(exc)
        except Exception:
            return (
                "failed",
                f"Copy failed; check local access and {self.destination_label} connectivity.",
            )

    def copy_results(self, archive, workers):
        # Inventory/database reads and reporting stay on the main thread. Batches
        # bound the number of queued files; only active workers open file streams.
        entries = iter(registered_files())
        with ThreadPoolExecutor(max_workers=workers) as pool:
            while batch := list(islice(entries, workers * 4)):
                for entry, result in zip(
                    batch, pool.map(lambda item: self.copy_file(item, archive), batch)
                ):
                    yield entry[0], result

    def handle(self, *args, **options):
        archive = None
        counts = Counter()
        workers = options.get("workers", 4)
        if workers not in range(1, 17):
            raise CommandError("Workers must be between 1 and 16.")
        try:
            if options["execute"]:
                try:
                    archive = self.get_archive()
                except ArchiveError as exc:
                    raise CommandError(str(exc)) from None
                except Exception:
                    # SDK errors can contain signed URLs or account configuration.
                    raise CommandError(
                        f"Cannot access {self.destination_label}. Check credentials, permissions, and configuration."
                    ) from None
            for index, (namespace, (result, error)) in enumerate(
                self.copy_results(archive, workers), start=1
            ):
                counts[result] += 1
                if error:
                    self.stderr.write(f"File {index} ({namespace}): {error}")
                if index % 100 == 0 and options.get("verbosity", 1) > 0:
                    self.stdout.write(f"Checked {index} files.")
        finally:
            if archive:
                archive.close()
        self.stdout.write(
            f"{'Copy' if options['execute'] else 'Dry run'}: "
            f"{counts['ready']} ready, {counts['copied']} copied, "
            f"{counts['verified']} already verified, {counts['failed']} failed. "
            "Local files and database references are unchanged."
        )
        if counts["failed"]:
            raise CommandError(
                "Some files could not be verified. Resolve failures and rerun."
            )
