"""Verify a portable archive, then restore it as a new private project."""

import hashlib
import json
import logging
import math
import re
import stat
import subprocess
import tempfile
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
from zipfile import BadZipFile, ZipFile
from zlib import error as ZipCompressionError

from django.conf import settings
from django.core.files import File
from django.core.files.storage import default_storage
from django.db import transaction
from PIL import Image, UnidentifiedImageError
from rest_framework.exceptions import ValidationError

from apps.videomanagement.models import (
    Avatar,
    Icon,
    Intro,
    MediaAsset,
    Music,
    MusicCatalogTrack,
    Outro,
    Scene,
    SceneImage,
    UserPrompt,
    Video,
    VideoStatus,
)
from apps.videomanagement.serializers.project_import import (
    MAX_PROJECT_BYTES,
    ProjectManifestSerializer,
)
from apps.videomanagement.services.captions.alignment import narration_identity
from apps.videomanagement.services.videos.preview import preview_timeline
from apps.videomanagement.utils.cuts import video_cut_source

logger = logging.getLogger(__name__)
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
MEDIA_SUFFIXES = IMAGE_SUFFIXES | {
    ".mp4",
    ".avi",
    ".m4v",
    ".mov",
    ".webm",
    ".mkv",
    ".mp3",
    ".wav",
    ".m4a",
    ".aac",
    ".ogg",
    ".flac",
}


def finite_number(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("Non-finite numbers are not supported.")
    return result


def validate_media(path):
    """Reject active content and ensure packaged bytes are actual media."""
    try:
        if path.suffix in IMAGE_SUFFIXES:
            with Image.open(path) as image:
                if image.width * image.height > 20_000_000:
                    raise ValidationError(
                        "Project images must be at most 20 megapixels."
                    )
                image.verify()
            return
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-protocol_whitelist",
                "file,pipe",
                "-format_whitelist",
                "mov,avi,m4v,matroska,wav,mp3,ogg,flac,aac",
                "-show_entries",
                "stream=codec_type",
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        streams = json.loads(result.stdout).get("streams", [])
        if not streams or any(
            stream.get("codec_type") not in {"audio", "video", "subtitle", "data"}
            for stream in streams
        ):
            raise ValueError("No supported media streams")
    except (
        OSError,
        ValueError,
        UnidentifiedImageError,
        Image.DecompressionBombError,
        subprocess.SubprocessError,
    ) as exc:
        raise ValidationError("The project contains an invalid media file.") from exc


def read_archive(bundle, directory):
    members = bundle.infolist()
    if len(members) > 10001 or len({entry.filename for entry in members}) != len(
        members
    ):
        raise ValidationError("The ZIP contains too many files or duplicate paths.")
    if sum(entry.file_size for entry in members) > MAX_PROJECT_BYTES:
        raise ValidationError("The unpacked project must be smaller than 1 GB.")
    for entry in members:
        if entry.flag_bits & 1 or stat.S_ISLNK(entry.external_attr >> 16):
            raise ValidationError(
                "Encrypted files and symbolic links are not supported."
            )
        if entry.filename != "project.json" and not re.fullmatch(
            r"media/[a-zA-Z0-9_-]+\.[a-zA-Z0-9]{1,10}", entry.filename
        ):
            raise ValidationError("The ZIP contains an unsafe or unexpected path.")
    try:
        if bundle.getinfo("project.json").file_size > 5 * 1024 * 1024:
            raise ValidationError("The project manifest is too large.")
        raw = json.loads(
            bundle.read("project.json"),
            parse_constant=finite_number,
            parse_float=finite_number,
        )
    except (KeyError, ValueError, UnicodeError, RecursionError) as exc:
        raise ValidationError("The ZIP needs a valid project.json manifest.") from exc
    # Imported icon IDs are validated against this archive, never another user's catalog.
    known_icons = (
        {
            row["key"]: True
            for row in raw.get("icons", [])
            if isinstance(row, dict) and isinstance(row.get("key"), str)
        }
        if isinstance(raw, dict) and isinstance(raw.get("icons"), list)
        else {}
    )
    serializer = ProjectManifestSerializer(
        data=raw, context={"diagram_icon_ids": known_icons}
    )
    serializer.is_valid(raise_exception=True)
    manifest = serializer.validated_data
    pending = [raw.get("scenes"), raw.get("project", {}).get("storyboard")]
    while pending:
        item = pending.pop()
        if isinstance(item, list):
            pending.extend(item)
        elif isinstance(item, dict):
            if item.get("icon") and (
                not isinstance(item["icon"], str) or item["icon"] not in known_icons
            ):
                raise ValidationError("A diagram icon is missing from the project ZIP.")
            pending.extend(item.values())
    files = manifest["files"]
    if {entry.filename for entry in members} != {
        "project.json",
        *(row["path"] for row in files),
    }:
        raise ValidationError("The files in the ZIP do not match its manifest.")
    paths = {}
    for entry in files:
        name = entry["path"]
        path = Path(directory, Path(name).name)
        if (
            path.suffix not in MEDIA_SUFFIXES
            or bundle.getinfo(name).file_size != entry["size"]
        ):
            raise ValidationError(
                "The project contains an unsupported file or incorrect size."
            )
        digest = hashlib.sha256()
        with bundle.open(name) as source, path.open("wb") as target:
            size = 0
            while chunk := source.read(256 * 1024):
                size += len(chunk)
                if size > entry["size"]:
                    raise ValidationError("A project file exceeds its declared size.")
                digest.update(chunk)
                target.write(chunk)
        if size != entry["size"] or digest.hexdigest() != entry["sha256"]:
            raise ValidationError("A project file failed its integrity check.")
        validate_media(path)
        paths[name] = path
    return manifest, paths


def media_references(manifest):
    project = manifest["project"]
    references = [
        project[key]
        for key in ("reference_image", "source_audio", "cover", "thumbnail", "output")
    ]
    references.extend(
        project[key]["file"]
        for key in ("music", "intro", "outro", "avatar")
        if project[key]
    )
    for scene in manifest["scenes"]:
        references.extend(
            scene[key] for key in ("narration", "voiceover", "overlay_logo")
        )
        references.extend(
            asset["file"]
            for asset in [
                scene["starting_asset"],
                *(visual["asset"] for visual in scene["visuals"]),
            ]
            if asset
        )
    references.extend(icon["file"] for icon in manifest["icons"])
    return {name for name in references if name is not None}


def remap_icons(value, keys):
    if isinstance(value, list):
        return [remap_icons(item, keys) for item in value]
    if isinstance(value, dict):
        return {
            key: keys.get(item, "") if key == "icon" else remap_icons(item, keys)
            for key, item in value.items()
        }
    return value


def restore_project(user, manifest, stored):
    project = dict(manifest["project"])
    storyboard = project.pop("storyboard")
    prompt = project.pop("prompt")
    resources = {key: project.pop(key) for key in ("music", "intro", "outro", "avatar")}
    for key in ("reference_image", "source_audio", "cover", "thumbnail", "output"):
        project[key] = stored.get(project[key], "")
    video = Video.objects.create(
        created_by=user,
        prompt=UserPrompt.objects.create(prompt=prompt),
        status=VideoStatus.READY,
        dir_name=str(Path(settings.MEDIA_ROOT, "media", "imports", uuid4().hex)),
        **project,
    )
    keys = {}
    for data in manifest["icons"]:
        data = dict(data)
        old_key = data.pop("key")
        icon = Icon.objects.create(
            key=f"custom:{uuid4().hex}",
            collection="custom",
            name="Imported icon",
            created_by=user,
            **{**data, "file": stored[data["file"]]},
        )
        keys[old_key] = icon.key
    video.gpt_answer = remap_icons(storyboard, keys)
    old_ids = {}
    for name, model in (
        ("music", Music),
        ("intro", Intro),
        ("outro", Outro),
        ("avatar", Avatar),
    ):
        data = resources[name]
        if not data:
            continue
        resource = model.objects.create(
            created_by=user, name=data["name"], file=stored.get(data["file"], "")
        )
        if name == "music" and data.get("license"):
            resource.catalog_track = MusicCatalogTrack.objects.create(
                source_id=f"import:{uuid4().hex}",
                title=data["name"],
                category="imported",
                **data["license"],
            )
            resource.save(update_fields=["catalog_track"])
        if data.get("id"):
            old_ids[str(resource.pk)] = str(data["id"])
        setattr(video, name, resource)
    video.save()
    assets = {}

    def asset(data):
        if not data or not data["file"]:
            return None
        name = data["file"]
        if name not in assets:
            assets[name] = MediaAsset.objects.create(
                created_by=user, source_video=video, **{**data, "file": stored[name]}
            )
        return assets[name]

    rows = sorted(manifest["scenes"], key=lambda row: row["position"])
    for index, data in enumerate(rows):
        data = dict(data)
        old_id = data.pop("id")
        data["position"] = index + 1
        visuals = data.pop("visuals")
        data["starting_asset"] = asset(data["starting_asset"])
        data["file"] = stored.get(data.pop("narration"), "")
        for key in ("voiceover", "overlay_logo"):
            data[key] = stored.get(data[key], "")
        alignment = data.pop("caption_alignment")
        data["overlays"] = remap_icons(data["overlays"], keys)
        scene = Scene.objects.create(
            video=video, is_last=index == len(rows) - 1, **data
        )
        old_ids[str(scene.pk)] = str(old_id)
        for visual in visuals:
            SceneImage.objects.create(
                scene=scene,
                prompt=visual["prompt"],
                with_audio=visual["with_audio"],
                asset=asset(visual["asset"]),
            )
        if alignment.get("source"):
            scene.caption_alignment = {
                "source": narration_identity(scene),
                "words": alignment.get("words", []),
            }
            scene.save(update_fields=["caption_alignment"])
    if video.cuts and rows:
        segments = preview_timeline(video).segments
        old_segments = [
            replace(
                segment,
                content=SimpleNamespace(
                    pk=old_ids.get(str(segment.content.pk), str(segment.content.pk)),
                    cuts=getattr(segment.content, "cuts", {}),
                ),
            )
            for segment in segments
        ]
        old_source = video_cut_source(old_segments)
        if video.cuts.get("source_key") == old_source["key"] and math.isclose(
            video.cuts["source_duration"], old_source["duration"], abs_tol=0.001
        ):
            video.cuts["source_key"] = video_cut_source(segments)["key"]
            video.save(update_fields=["cuts"])
    return video


def import_project(user, upload):
    stored = {}
    try:
        with (
            tempfile.TemporaryDirectory(prefix="viddie-import-") as directory,
            ZipFile(upload) as bundle,
        ):
            manifest, paths = read_archive(bundle, directory)
            if media_references(manifest) != set(paths):
                raise ValidationError(
                    "The project media references do not match its packaged files."
                )
            # All files are verified before the first persistent write. Names are
            # generated here; no archive path can overwrite an existing object.
            prefix = f"media/imports/{uuid4().hex}"
            try:
                for name, path in paths.items():
                    with path.open("rb") as source:
                        stored[name] = default_storage.save(
                            f"{prefix}/{path.name}", File(source)
                        )
                with transaction.atomic():
                    return restore_project(user, manifest, stored)
            except Exception:
                # Only this attempt's uploads are eligible for cleanup. The
                # configured storage retention policy still applies (R2 retains files).
                for name in stored.values():
                    try:
                        default_storage.delete(name)
                    except Exception:
                        logger.exception("Could not clean up imported media %s", name)
                raise
    except (BadZipFile, ZipCompressionError, NotImplementedError, EOFError) as exc:
        raise ValidationError(
            "Choose a valid, unencrypted Viddie project ZIP."
        ) from exc
