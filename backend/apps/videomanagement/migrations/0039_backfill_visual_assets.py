"""Copy existing project visuals into independent, reusable library assets."""

import hashlib
import logging
from pathlib import Path
from uuid import uuid4

from django.core.exceptions import SuspiciousFileOperation
from django.db import IntegrityError, migrations, transaction

logger = logging.getLogger(__name__)
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".webm", ".m4v"}
VISUAL_KINDS = dict.fromkeys(IMAGE_EXTENSIONS, "IMAGE") | dict.fromkeys(
    VIDEO_EXTENSIONS, "VIDEO"
)


# Keep this implementation frozen against historical models; runtime retention
# helpers will continue to evolve after this migration has shipped.
def digest_file(source):
    digest = hashlib.sha256()
    for chunk in source.chunks():
        digest.update(chunk)
    source.seek(0)
    return digest.hexdigest()


def usable(field):
    try:
        return bool(field and field.storage.exists(field.name))
    except (OSError, ValueError, SuspiciousFileOperation):
        return False


def backfill_visual_assets(apps, schema_editor):
    Asset = apps.get_model("videomanagement", "MediaAsset")
    Visual = apps.get_model("videomanagement", "SceneImage")
    Video = apps.get_model("videomanagement", "Video")
    alias = schema_editor.connection.alias
    assets = Asset.objects.using(alias)
    skipped = 0

    # Existing library entries win deduplication and retain their titles/tags.
    for asset in assets.filter(
        kind__in=("IMAGE", "VIDEO"), checksum__isnull=True
    ).iterator():
        if not asset.created_by_id or not usable(asset.file):
            continue
        with asset.file.open("rb") as source:
            checksum = digest_file(source)
        try:
            with transaction.atomic(using=alias):
                assets.filter(pk=asset.pk).update(checksum=checksum)
        except IntegrityError:
            # Preserve older duplicate library entries rather than deleting user data.
            continue

    def archive(video, field, label):
        nonlocal skipped
        if not video.created_by_id or not usable(field):
            if field:
                skipped += 1
            return None
        extension = Path(field.name).suffix.lower()
        kind = VISUAL_KINDS.get(extension)
        if not kind:
            return None
        with field.open("rb") as source:
            checksum = digest_file(source)
            existing = assets.filter(
                created_by_id=video.created_by_id, checksum=checksum
            ).first()
            if existing and existing.file.name != field.name:
                return existing
            # An existing entry sharing the project path also needs its own copy.
            asset = existing or Asset(
                created_by_id=video.created_by_id,
                checksum=checksum,
                source_video_id=video.pk,
                title=f"{video.title} · {label.title()}"[:100],
                tags=[label],
                kind=kind,
                created_at=video.created_at,
            )
            asset.file.save(f"{uuid4().hex}{extension}", source, save=False)
            try:
                with transaction.atomic(using=alias):
                    asset.save(using=alias)
            except IntegrityError:
                asset.file.storage.delete(asset.file.name)
                existing = assets.filter(
                    created_by_id=video.created_by_id, checksum=checksum
                ).first()
                if existing:
                    return existing
                raise
            except Exception:
                asset.file.storage.delete(asset.file.name)
                raise
            return asset

    visuals = (
        Visual.objects.using(alias)
        .select_related("scene__video")
        .order_by("scene__video_id", "scene__position", "created_at", "pk")
    )
    for visual in visuals.iterator(chunk_size=200):
        label = (
            "scene video"
            if Path(visual.file.name or "").suffix.lower() in VIDEO_EXTENSIONS
            else "scene image"
        )
        asset = archive(visual.scene.video, visual.file, label)
        if asset:
            Visual.objects.using(alias).filter(pk=visual.pk).update(asset_id=asset.pk)
    for video in Video.objects.using(alias).iterator(chunk_size=200):
        archive(video, video.reference_image, "reference image")
        archive(video, video.cover, "video cover")
    if skipped:
        logger.warning(
            "Visual asset migration skipped %s missing or ownerless project files",
            skipped,
        )


class Migration(migrations.Migration):
    atomic = False
    dependencies = [("videomanagement", "0038_persistent_visual_assets")]
    # Keep archived files if the schema is rolled back; deleting them loses history.
    operations = [
        migrations.RunPython(backfill_visual_assets, migrations.RunPython.noop)
    ]
