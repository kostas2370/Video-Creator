"""Safe local media paths and verified R2 transfers."""

import hashlib
import os
from pathlib import Path, PurePosixPath


class ArchiveError(Exception):
    """An archive cannot be copied or verified safely."""


def relative_name(storage, name):
    """Handle legacy absolute FileField values only inside their declared root."""
    path = Path(name)
    if ".." in path.parts:
        raise ArchiveError("Unsafe media name; no file was copied.")
    if path.is_absolute():
        try:
            return path.relative_to(Path(storage.location).absolute()).as_posix()
        except ValueError:
            raise ArchiveError(
                "Absolute media path is outside its storage root."
            ) from None
    return name


def blob_name(namespace, name):
    # MEDIA_ROOT currently includes the backend source tree. Only database-backed
    # file names may be supplied; never recursively upload that directory.
    path = PurePosixPath(name)
    if (
        namespace not in {"media", "clips", "publishing"}
        or not name
        or path.is_absolute()
        or ".." in path.parts
        or "\\" in name
        or str(path) != name
    ):
        raise ArchiveError("Unsafe media name; no file was copied.")
    return f"{namespace}/{name}"


def local_path(storage, name):
    declared_root = Path(storage.location).absolute()
    root = declared_root.resolve()
    path = Path(storage.path(name))
    resolved = path.resolve()
    if not resolved.is_relative_to(root):
        raise ArchiveError("Media path escapes its storage root.")
    # Reject symlinks, including ones in intermediate directories.
    relative = path.absolute().relative_to(declared_root)
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ArchiveError("Symlinked media must be reviewed before copying.")
    if not resolved.is_file():
        raise ArchiveError("Registered media file is missing.")
    return resolved


def fingerprint(stream):
    digest = hashlib.sha256()
    size = 0
    while chunk := stream.read(4 * 1024 * 1024):
        digest.update(chunk)
        size += len(chunk)
    return size, digest.hexdigest()


def path_state(path):
    stat = path.stat()
    return stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns


def file_state(stream):
    stat = os.fstat(stream.fileno())
    return stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns


def copy_verified(path, name, archive):
    """Resume at file boundaries; conflicting blobs are never overwritten."""
    with path.open("rb") as source:
        before = file_state(source)
        size, digest = fingerprint(source)
        if file_state(source) != before:
            raise ArchiveError("Local file changed while being read; rerun when idle.")
        source.seek(0)
        uploaded = archive.upload_if_missing(name, source, size, digest)
        # Read the actual remote bytes on every run, rather than trusting metadata
        # or file size. This also verifies uploads left by interrupted saves.
        remote_size = 0
        remote_digest = hashlib.sha256()
        for chunk in archive.chunks(name):
            remote_size += len(chunk)
            remote_digest.update(chunk)
        if file_state(source) != before:
            raise ArchiveError(
                "Local file changed during upload; keep both copies and review."
            )
        if (remote_size, remote_digest.hexdigest()) != (size, digest):
            raise ArchiveError(
                "Remote content differs from local media; no overwrite performed."
            )
    return "copied" if uploaded else "verified"
