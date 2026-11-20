"""Portable project snapshots and bounded-memory ZIP streaming."""

import asyncio
import hashlib
import json
import re
from contextlib import closing
from pathlib import Path
from urllib.parse import urlencode
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.db.models import Q
from django.http import StreamingHttpResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.http import content_disposition_header
from django.utils.text import slugify
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.common.r2_storage import R2StorageMixin
from apps.videomanagement.models import IN_FLIGHT_STATUSES, Icon, Video
from apps.videomanagement.serializers.project_archive import (
    ProjectSceneSerializer,
    ProjectVideoSerializer,
)


class ZipBuffer:
    def __init__(self):
        self.chunks = []

    def write(self, data):
        if data:
            self.chunks.append(data)
        return len(data)

    def flush(self):
        pass

    def drain(self):
        chunks, self.chunks = self.chunks, []
        return chunks


class ProjectArchive:
    def __init__(self):
        self.files = {}

    def media(self, field):
        if not field:
            return None
        key = (field.storage, field.name)
        if key not in self.files:
            suffix = Path(field.name).suffix.lower()
            suffix = suffix if re.fullmatch(r"\.[a-z0-9]{1,10}", suffix) else ""
            entry = {"path": f"media/{len(self.files) + 1:04d}{suffix}"}
            self.files[key] = (field, entry)
        return self.files[key][1]["path"]

    def asset(self, asset):
        if not asset:
            return None
        return {
            "file": self.media(asset.file),
            "title": asset.title,
            "kind": asset.kind,
            "tags": asset.tags,
            "duration": asset.duration,
        }

    def preflight(self):
        for field, entry in self.files.values():
            storage = field.storage
            remote = isinstance(storage, R2StorageMixin) and storage.r2_enabled
            info = storage.remote_info(field.name) if remote else None
            if (remote and info is None) or (
                not remote and not storage.exists(field.name)
            ):
                raise ValidationError(
                    "Some project media is missing. Restore it before exporting the project."
                )
            if remote:
                entry.update(
                    size=info["ContentLength"],
                    etag=info["ETag"],
                    expected_hash=info.get("Metadata", {}).get("sha256"),
                )
            else:
                stat = Path(field.path).stat()
                entry.update(size=stat.st_size, modified_ns=stat.st_mtime_ns)


def prepare_project_export(video, *, include_output=False):
    archive = ProjectArchive()
    with transaction.atomic():
        video = Video.objects.select_for_update().get(pk=video.pk)
        if video.status in IN_FLIGHT_STATUSES:
            raise ValidationError(
                "Wait for video processing to finish before exporting the project."
            )
        video = (
            Video.objects.select_related(
                "prompt",
                "voice_model",
                "music__catalog_track",
                "avatar",
                "intro",
                "outro",
            )
            .with_editor_media()
            .get(pk=video.pk)
        )
        manifest = {
            "format": "viddie-project",
            "version": 1,
            "exported_at": timezone.now().isoformat(),
            "project": dict(ProjectVideoSerializer(video).data),
            "scenes": [],
            "icons": [],
        }
        project = manifest["project"]
        for name in ("reference_image", "source_audio", "cover", "thumbnail"):
            project[name] = archive.media(getattr(video, name))
        project["output"] = archive.media(video.output) if include_output else None
        for name in ("avatar", "intro", "outro", "music"):
            resource = getattr(video, name)
            project[name] = (
                {
                    "id": str(resource.pk),
                    "name": resource.name,
                    "file": archive.media(resource.file),
                }
                if resource
                else None
            )
        if video.music and video.music.catalog_track:
            track = video.music.catalog_track
            project["music"]["license"] = {
                "attribution": track.attribution,
                "license_url": track.license_url,
                "source_url": track.source_url,
            }
        icon_keys = set()
        for scene in video.scenes.all():
            data = dict(ProjectSceneSerializer(scene).data)
            data.update(
                narration=archive.media(scene.file),
                voiceover=archive.media(scene.voiceover),
                overlay_logo=archive.media(scene.overlay_logo),
                starting_asset=archive.asset(scene.starting_asset),
                visuals=[
                    {
                        "prompt": visual.prompt,
                        "with_audio": visual.with_audio,
                        "asset": archive.asset(visual.asset),
                    }
                    for visual in scene.scene_images.all()
                ],
            )
            for overlay in scene.overlays:
                icon_keys.update(
                    item["icon"]
                    for item in overlay.get("diagram", {}).get("items", [])
                    if item.get("icon")
                )
            manifest["scenes"].append(data)
        for group in (project.get("storyboard") or {}).get("scenes", []):
            for sentence in group.get("sentences", []):
                diagram = (sentence.get("editing") or {}).get("diagram") or {}
                icon_keys.update(
                    item["icon"]
                    for item in diagram.get("items", [])
                    if item.get("icon")
                )
        icons = list(
            Icon.objects.filter(
                Q(created_by__isnull=True) | Q(created_by_id=video.created_by_id),
                key__in=icon_keys,
            ).order_by("key")
        )
        if {icon.key for icon in icons if icon.file} != icon_keys:
            raise ValidationError(
                "Some diagram icons are missing. Restore them before exporting the project."
            )
        for icon in icons:
            manifest["icons"].append(
                {
                    "key": icon.key,
                    "file": archive.media(icon.file),
                    "license": icon.license,
                    "license_url": icon.license_url,
                    "attribution": icon.attribution,
                }
            )
    archive.preflight()
    return manifest, archive


def source_chunks(field, entry):
    storage = field.storage
    if "etag" in entry:
        if entry["size"]:
            yield from storage.remote_chunks(
                field.name, 0, entry["size"] - 1, entry["etag"]
            )
    else:
        with storage.open(field.name, "rb") as source:
            stat = Path(field.path).stat()
            if (stat.st_size, stat.st_mtime_ns) != (
                entry["size"],
                entry["modified_ns"],
            ):
                raise OSError("Project media changed during export.")
            yield from source.chunks(256 * 1024)
            after = Path(field.path).stat()
            if (after.st_size, after.st_mtime_ns) != (
                entry["size"],
                entry["modified_ns"],
            ):
                raise OSError("Project media changed during export.")


def zip_chunks(manifest, archive):
    buffer = ZipBuffer()
    with ZipFile(buffer, "w", compression=ZIP_STORED, allowZip64=True) as bundle:
        files = []
        for field, entry in archive.files.values():
            digest, size = hashlib.sha256(), 0
            with bundle.open(entry["path"], "w", force_zip64=True) as target:
                yield from buffer.drain()
                with closing(source_chunks(field, entry)) as chunks:
                    for chunk in chunks:
                        digest.update(chunk)
                        size += len(chunk)
                        target.write(chunk)
                        yield from buffer.drain()
                if size != entry["size"] or (
                    entry.get("expected_hash")
                    and digest.hexdigest() != entry["expected_hash"]
                ):
                    raise OSError("Project media failed export verification.")
            files.append(
                {"path": entry["path"], "size": size, "sha256": digest.hexdigest()}
            )
            yield from buffer.drain()
        manifest = {**manifest, "files": files}
        bundle.writestr(
            "project.json",
            json.dumps(manifest, cls=DjangoJSONEncoder, ensure_ascii=False, indent=2),
            compress_type=ZIP_DEFLATED,
        )
        yield from buffer.drain()
    yield from buffer.drain()


async def project_zip_chunks(manifest, archive):
    chunks = zip_chunks(manifest, archive)
    sentinel = object()
    try:
        while (
            chunk := await asyncio.to_thread(next, chunks, sentinel)
        ) is not sentinel:
            yield chunk
    finally:
        await asyncio.to_thread(chunks.close)


def project_export_response(request, video, *, include_output=False, check_only=False):
    manifest, archive = prepare_project_export(video, include_output=include_output)
    filename = f"{slugify(video.title, allow_unicode=True)[:80] or 'video'}-project.zip"
    if check_only:
        url = reverse("video-export-project", args=[video.pk])
        return Response(
            {
                "download_url": request.build_absolute_uri(url)
                + "?"
                + urlencode({"include_output": str(include_output).lower()}),
                "filename": filename,
            },
            headers={"Cache-Control": "no-store"},
        )
    response = StreamingHttpResponse(
        project_zip_chunks(manifest, archive), content_type="application/zip"
    )
    response["Content-Disposition"] = content_disposition_header(True, filename)
    response["Cache-Control"] = "private, no-store"
    response["Referrer-Policy"] = "no-referrer"
    response["X-Content-Type-Options"] = "nosniff"
    response["X-Accel-Buffering"] = "no"
    return response
