"""Keep independent, owner-scoped library copies of project visuals."""

import hashlib
from pathlib import Path
from uuid import uuid4

from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction

from apps.videomanagement.models import MediaAsset, SceneImage
from apps.videomanagement.utils.file_utils import (
    check_if_image,
    check_if_video,
    stored_file_exists,
)
from apps.videomanagement.utils.timing import file_timing


VIDEO_VISUAL_LABELS = {"reference_image": "reference image", "cover": "video cover"}


def visual_kind(name):
    if check_if_image(name):
        return MediaAsset.Kind.IMAGE
    if check_if_video(name):
        return MediaAsset.Kind.VIDEO
    return None


def save_visual_asset(
    *, user, upload, title, tags, kind, duration=None, source_video=None
):
    """Deduplicate by owner and bytes, without sharing project file paths."""
    digest = hashlib.sha256()
    upload.seek(0)
    for chunk in upload.chunks():
        digest.update(chunk)
    upload.seek(0)
    checksum = digest.hexdigest()
    existing = MediaAsset.objects.filter(created_by=user, checksum=checksum).first()
    if existing and stored_file_exists(existing.file):
        return existing
    asset = existing or MediaAsset(
        created_by=user,
        checksum=checksum,
        title=title[:100],
        tags=tags,
        kind=kind,
        duration=duration,
        source_video=source_video,
    )
    name = f"{uuid4().hex}{Path(upload.name).suffix.lower()}"
    asset.file.save(name, upload, save=False)
    saved_name = asset.file.name
    try:
        with transaction.atomic():
            asset.save()
    except IntegrityError:
        asset.file.storage.delete(saved_name)
        # A concurrent request may have archived the same bytes first.
        winner = MediaAsset.objects.filter(created_by=user, checksum=checksum).first()
        if winner:
            return winner
        raise
    except Exception:
        asset.file.storage.delete(saved_name)
        raise
    finally:
        upload.seek(0)
    return asset


def retain_stored_visual(video, field, *, title, tags):
    if not video.created_by_id or not stored_file_exists(field):
        return None
    kind = visual_kind(field.name)
    if not kind:
        return None
    duration = (
        file_timing(field).get("duration") if kind == MediaAsset.Kind.VIDEO else None
    )
    with field.open("rb") as upload:
        return save_visual_asset(
            user=video.created_by,
            upload=upload,
            title=title,
            tags=tags,
            kind=kind,
            duration=duration,
            source_video=video if video.pk else None,
        )


def retain_scene_visual(visual, source):
    video = visual.scene.video
    label = "scene video" if check_if_video(source.name or "") else "scene image"
    asset = retain_stored_visual(
        video,
        source,
        title=f"{video.title} · Scene {visual.scene.position}",
        tags=[label],
    )
    if asset:
        SceneImage.objects.filter(pk=visual.pk, file=source.name).update(asset=asset)
        if visual.file.name == source.name:
            visual.asset_id = asset.pk


def retain_video_visual(video, field_name, source):
    label = VIDEO_VISUAL_LABELS[field_name]
    return retain_stored_visual(
        video,
        source,
        title=f"{video.title} · {label.title()}",
        tags=[label],
    )


def retain_generated_cover(video, image):
    return save_visual_asset(
        user=video.created_by,
        upload=ContentFile(image, name="thumbnail.png"),
        title=f"{video.title} · AI thumbnail",
        tags=["ai thumbnail"],
        kind=MediaAsset.Kind.IMAGE,
        source_video=video,
    )
