"""Private R2 storage with a retained, on-demand local processing cache."""

import hashlib
import os
import shutil
import tempfile
from functools import lru_cache
from pathlib import Path
from threading import RLock
from uuid import uuid4

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
        from botocore.exceptions import ClientError

        try:
            return self.archive.client.head_object(
                Bucket=self.archive.bucket, Key=self.object_key(name)
            )
        except ClientError as exc:
            if exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode") == 404:
                return None
            raise

    def path(self, name):
        name = relative_name(self, name)
        self.object_key(name)
        path = Path(super().path(name))
        if not self.r2_enabled or path.exists():
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
        descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".r2-")
        try:
            response = self.archive.client.get_object(
                Bucket=self.archive.bucket,
                Key=self.object_key(name),
                IfMatch=info["ETag"],
            )
            body = response["Body"]
            try:
                with os.fdopen(descriptor, "wb") as destination:
                    descriptor = None
                    for chunk in body.iter_chunks(chunk_size=4 * 1024 * 1024):
                        destination.write(chunk)
                        digest.update(chunk)
                        size += len(chunk)
            finally:
                body.close()
            expected = info.get("Metadata", {}).get("sha256")
            if (
                size != info["ContentLength"]
                or not expected
                or digest.hexdigest() != expected
            ):
                raise ArchiveError(
                    "R2 download failed verification; local files retained."
                )
            # Link atomically without replacing another worker's existing file.
            try:
                os.link(temporary, path)
            except FileExistsError:
                pass
        finally:
            if descriptor is not None:
                os.close(descriptor)
            os.unlink(temporary)
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
        stat = path.stat()
        state = (stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
        cache_key = (self.archive.bucket, self.namespace, str(path))
        with _verified_lock:
            if _verified.get(cache_key) == state:
                return name
        with path.open("rb") as source:
            size, digest = fingerprint(source)
        after_hash = path.stat()
        if (
            after_hash.st_size,
            after_hash.st_mtime_ns,
            after_hash.st_ctime_ns,
        ) != state:
            raise ArchiveError("Local media changed while being read.")
        original_path = path
        info = self.remote_info(name)
        if info and (info.get("Metadata", {}).get("sha256"), info["ContentLength"]) == (
            digest,
            size,
        ):
            # Existing migration objects were verified byte for byte on upload.
            pass
        else:
            if info:
                # A renderer reused a local filename. Keep the previous remote
                # version and local original; point this field at a fresh copy.
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
            copy_verified(path, self.object_key(name), self.archive)
        final_stat = path.stat()
        original_stat = original_path.stat()
        if (
            original_stat.st_size,
            original_stat.st_mtime_ns,
            original_stat.st_ctime_ns,
        ) != state:
            raise ArchiveError("Local media changed during upload.")
        with _verified_lock:
            if len(_verified) >= 2048:
                _verified.clear()
            _verified[(self.archive.bucket, self.namespace, str(path))] = (
                final_stat.st_size,
                final_stat.st_mtime_ns,
                final_stat.st_ctime_ns,
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
