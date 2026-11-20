"""Private R2 storage with a retained, on-demand local processing cache."""

import hashlib
import os
import shutil
import tempfile
from contextlib import closing
from functools import lru_cache
from pathlib import Path
from threading import RLock
from uuid import uuid4

from botocore.exceptions import ClientError
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db.models import FileField
from django.utils.deconstruct import deconstructible

from .media_archive import (
    ArchiveError,
    blob_name,
    copy_verified,
    fingerprint,
    local_path,
    path_state,
    relative_name,
)
from .r2_archive import R2Archive


@lru_cache(maxsize=4)
def _archive(account, bucket, key, secret, jurisdiction, pid):
    # Each worker process owns its client; never share an inherited connection.
    return R2Archive(account, bucket, key, secret, jurisdiction)


class R2StorageMixin:
    namespace = "media"

    @property
    def r2_enabled(self):
        return getattr(settings, "R2_STORAGE_ENABLED", False)

    @property
    def archive(self):
        return _archive(
            settings.R2_ACCOUNT_ID,
            settings.R2_BUCKET_NAME,
            settings.R2_ACCESS_KEY_ID,
            settings.R2_SECRET_ACCESS_KEY,
            settings.R2_JURISDICTION,
            os.getpid(),
        )

    def object_key(self, name):
        return blob_name(self.namespace, relative_name(self, name))

    def remote_info(self, name):
        try:
            return self.archive.client.head_object(
                Bucket=self.archive.bucket, Key=self.object_key(name)
            )
        except ClientError as exc:
            if exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode") == 404:
                return None
            raise

    def path(self, name):
        if not self.r2_enabled:
            return super().path(name)
        name = relative_name(self, name)
        self.object_key(name)
        path = Path(super().path(name))
        if path.exists():
            return str(path)
        info = self.remote_info(name)
        if info is None:
            # Callers also use .path to choose destinations for newly generated files.
            return str(path)
        root = Path(self.location).resolve()
        if not path.resolve().is_relative_to(root):
            raise ArchiveError("Media path escapes its storage root.")
        path.parent.mkdir(parents=True, exist_ok=True)
        digest, size = hashlib.sha256(), 0
        response = self.archive.client.get_object(
            Bucket=self.archive.bucket,
            Key=self.object_key(name),
            IfMatch=info["ETag"],
        )
        with (
            closing(response["Body"]) as body,
            tempfile.NamedTemporaryFile(dir=path.parent, prefix=".r2-") as destination,
        ):
            for chunk in body.iter_chunks(chunk_size=4 * 1024 * 1024):
                destination.write(chunk)
                digest.update(chunk)
                size += len(chunk)
            if size != info["ContentLength"] or digest.hexdigest() != info.get(
                "Metadata", {}
            ).get("sha256"):
                raise ArchiveError(
                    "R2 download failed verification; local files retained."
                )
            destination.flush()
            # Publish the verified file without replacing another worker's cache.
            try:
                os.link(destination.name, path)
            except FileExistsError:
                pass
        return str(path)

    def exists(self, name):
        if not self.r2_enabled:
            return super().exists(name)
        self.object_key(name)
        return (
            os.path.exists(super().path(relative_name(self, name)))
            or self.remote_info(name) is not None
        )

    def _save(self, name, content):
        name = super()._save(name, content)
        return self.sync(name) if self.r2_enabled else name

    def size(self, name):
        if self.r2_enabled:
            info = self.remote_info(name)
            if info is not None:
                return info["ContentLength"]
        return super().size(name)

    def delete(self, name):
        # django-cleanup also calls this on replacements and model deletion.
        # Retain both copies until a separate, verified retention policy exists.
        if not self.r2_enabled:
            return super().delete(name)

    def sync(self, name):
        """Publish directly generated files too; never replace an existing object."""
        name = relative_name(self, name)
        path = local_path(self, name)
        state = path_state(path)
        cache_key = (self.archive.bucket, self.namespace, str(path))
        with _verified_lock:
            if _verified.get(cache_key) == state:
                return name
        original_path = path
        info = self.remote_info(name)
        matches = False
        if info:
            with path.open("rb") as source:
                size, digest = fingerprint(source)
            if path_state(path) != state:
                raise ArchiveError("Local media changed while being read.")
            matches = (
                info.get("Metadata", {}).get("sha256"),
                info["ContentLength"],
            ) == (digest, size)
            if not matches:
                # Keep the previous remote version when a renderer reuses a filename.
                original = Path(name)
                name = str(
                    original.with_name(
                        f"{original.stem}-{uuid4().hex}{original.suffix}"
                    )
                )
                destination = Path(super().path(name))
                with path.open("rb") as source, destination.open("xb") as target:
                    shutil.copyfileobj(source, target, length=4 * 1024 * 1024)
                path = destination
        if not matches:
            # This hashes a new file once and verifies the remote bytes after upload.
            copy_verified(path, self.object_key(name), self.archive)
        if path_state(original_path) != state:
            raise ArchiveError("Local media changed during upload.")
        with _verified_lock:
            if len(_verified) >= 2048:
                _verified.clear()
            _verified[(self.archive.bucket, self.namespace, str(path))] = path_state(
                path
            )
        return name

    def remote_chunks(self, name, start, end, etag):
        response = self.archive.client.get_object(
            Bucket=self.archive.bucket,
            Key=self.object_key(name),
            Range=f"bytes={start}-{end}",
            IfMatch=etag,
        )
        body = response["Body"]
        try:
            yield from body.iter_chunks(chunk_size=256 * 1024)
        finally:
            body.close()


_verified = {}
_verified_lock = RLock()


@deconstructible
class MediaStorage(R2StorageMixin, FileSystemStorage):
    pass


def sync_model_files(sender, instance, raw=False, update_fields=None, **kwargs):
    if raw or not getattr(settings, "R2_STORAGE_ENABLED", False):
        return
    if sender._meta.app_label not in {
        "videomanagement",
        "series",
        "clips",
        "publishing",
    }:
        return
    for field in sender._meta.concrete_fields:
        if not isinstance(field, FileField) or (
            update_fields is not None and field.name not in update_fields
        ):
            continue
        value = getattr(instance, field.attname)
        if value and value._committed and isinstance(value.storage, R2StorageMixin):
            value.name = value.storage.sync(value.name)
