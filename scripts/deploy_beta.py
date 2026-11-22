#!/usr/bin/env python3
import fcntl
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path, PurePosixPath
from urllib.request import urlopen
from uuid import uuid4

STATE = Path("/opt/viddie/backend")
CURRENT = Path("/opt/viddie-current")
RELEASES = Path("/opt/viddie-releases")
BACKUPS = Path("/var/backups/viddie")
MAX_ARCHIVE = 100 * 1024 * 1024
MAX_CONTENT = 512 * 1024 * 1024
PRIVATE_PARTS = {
    ".env",
    ".git",
    ".ssh",
    ".aws",
    "node_modules",
    "__pycache__",
    ".db-backups",
}
DATA_DIRS = {
    "media",
    "staticfiles",
    "private-clips",
    "private-publishing",
    "private-render-cache",
}
SERVICES = [
    "video_creator",
    "celery",
    "celery-render",
    "celery-beat",
    "frontend",
    "caddy",
]
WORKER_CHECK = """
import json, redis
from video_creator.celery import app
inspect = app.control.inspect(timeout=5)
counts = []
for method in ('active', 'reserved', 'scheduled'):
    replies = getattr(inspect, method)()
    if not replies or len(replies) < 2:
        raise RuntimeError('Both workers must respond before deployment')
    counts.append(sum(len(tasks) for tasks in replies.values()))
broker = redis.Redis.from_url(app.conf.broker_url)
counts.append(sum(broker.llen(queue) for queue in ('celery', 'renders')))
print(json.dumps(counts))
"""


def release_sha(command):
    match = re.fullmatch(r"deploy ([0-9a-f]{40})", command)
    if not match:
        raise ValueError("Only status or deploy followed by a commit SHA is accepted")
    return match[1]


def unpack(archive, destination):
    total = 0
    seen = set()
    with tarfile.open(archive, "r:gz") as bundle:
        for member in bundle:
            name = member.name.rstrip("/")
            path = PurePosixPath(name)
            if (
                not name
                or path.is_absolute()
                or ".." in path.parts
                or str(path) != name
                or set(path.parts) & PRIVATE_PARTS
                or (
                    len(path.parts) > 1
                    and path.parts[0] == "backend"
                    and path.parts[1] in DATA_DIRS
                )
                or not (member.isfile() or member.isdir())
                or name in seen
            ):
                raise ValueError("Unsafe release archive member")
            seen.add(name)
            total += member.size
            if total > MAX_CONTENT:
                raise ValueError("Release contents exceed the size limit")
            target = destination.joinpath(*path.parts)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with bundle.extractfile(member) as source, target.open("xb") as output:
                    shutil.copyfileobj(source, output)
                target.chmod(0o755 if member.mode & 0o111 else 0o644)
    for required in (
        "backend/manage.py",
        "backend/docker-compose.beta.yml",
        "backend/Dockerfile",
        "frontend/Dockerfile",
    ):
        if not (destination / required).is_file():
            raise ValueError("Release archive is missing required application files")


def receive(stream, destination):
    size = 0
    with destination.open("xb") as target:
        while chunk := stream.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_ARCHIVE:
                raise ValueError("Release archive exceeds the size limit")
            target.write(chunk)


def compose(backend, *args, capture=False, output=None):
    environment = {**os.environ, "VIDDIE_STATE_ROOT": str(STATE)}
    result = subprocess.run(
        [
            "docker",
            "compose",
            "--project-name",
            "viddie-beta",
            "-f",
            str(backend / "docker-compose.beta.yml"),
            *args,
        ],
        cwd=backend,
        env=environment,
        check=True,
        stdout=subprocess.PIPE if capture else output,
        text=capture,
    )
    return result.stdout if capture else None


def wait_idle(backend, timeout=600):
    deadline = time.monotonic() + timeout
    while True:
        raw = compose(
            backend, "exec", "-T", "celery", "python", "-c", WORKER_CHECK, capture=True
        )
        if not any(json.loads(raw)):
            return
        if time.monotonic() >= deadline:
            raise TimeoutError("Jobs did not finish; deployment cancelled")
        print("Waiting for queued and active jobs to finish", flush=True)
        time.sleep(5)


def wait_http(url, timeout=90):
    deadline = time.monotonic() + timeout
    while True:
        try:
            with urlopen(url + "/api/deployment/", timeout=10) as response:
                data = json.load(response)
                if response.status == 200 and all(
                    isinstance(data.get(key), bool)
                    for key in (
                        "sadtalker_enabled",
                        "service_keys_allowed",
                        "invite_only",
                    )
                ):
                    return
        except (OSError, ValueError):
            pass
        if time.monotonic() >= deadline:
            raise TimeoutError("HTTPS API health check failed")
        time.sleep(2)


def public_url(backend):
    url = compose(
        backend,
        "exec",
        "-T",
        "video_creator",
        "python",
        "-c",
        "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE','video_creator.settings'); import django; django.setup(); from django.conf import settings; assert settings.R2_STORAGE_ENABLED; print(settings.FRONTEND_URL)",
        capture=True,
    ).strip()
    if not re.fullmatch(r"https://[A-Za-z0-9.-]+", url):
        raise ValueError("Production URL must be an HTTPS hostname")
    return url


def deploy(sha, stream):
    RELEASES.mkdir(parents=True, exist_ok=True)
    backend = None
    with tempfile.TemporaryDirectory(prefix="incoming-", dir=RELEASES) as temporary:
        archive = Path(temporary) / "release.tar.gz"
        receive(stream, archive)
        marker = STATE / ".deployed-sha"
        if marker.is_file() and marker.read_text().strip() == sha:
            try:
                wait_http(public_url(CURRENT.resolve() / "backend"), timeout=15)
            except (OSError, ValueError, TimeoutError, subprocess.CalledProcessError):
                pass
            else:
                print(f"Revision {sha} is already deployed and healthy", flush=True)
                return
        release = RELEASES / f"{sha}-{uuid4().hex[:8]}"
        release.mkdir()
        try:
            unpack(archive, release)
        except Exception:
            shutil.rmtree(release)
            raise
    backend = release / "backend"
    print(f"Staged release at {release}", flush=True)
    (backend / ".env").symlink_to(STATE / ".env")
    for directory in DATA_DIRS:
        (STATE / directory).mkdir(parents=True, exist_ok=True)
        (backend / directory).mkdir(exist_ok=True)
    compose(backend, "config", "--quiet")
    compose(backend, "build", "--pull", "video_creator", "frontend")
    compose(
        backend,
        "run",
        "--rm",
        "--no-deps",
        "-T",
        "video_creator",
        "python",
        "-c",
        "pass",
    )
    previous = CURRENT.resolve() / "backend"
    compose(previous, "stop", "video_creator", "celery-beat")
    try:
        wait_idle(previous)
    except Exception:
        compose(previous, "start", "video_creator", "celery-beat")
        raise
    compose(previous, "stop", "--timeout", "60", "celery", "celery-render")
    backup = BACKUPS / f"{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{sha[:12]}"
    try:
        backup.mkdir(parents=True)
        shutil.copy2(STATE / ".env", backup / "env")
        with (backup / "database.dump").open("wb") as output:
            compose(
                previous,
                "exec",
                "-T",
                "postgres",
                "sh",
                "-c",
                'pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB"',
                output=output,
            )
        if not (backup / "database.dump").stat().st_size:
            raise RuntimeError("Database backup is empty; deployment cancelled")
    except Exception:
        compose(
            previous, "start", "video_creator", "celery", "celery-render", "celery-beat"
        )
        raise
    print(f"Database and environment backup saved at {backup}", flush=True)
    try:
        compose(
            backend,
            "run",
            "--rm",
            "-T",
            "video_creator",
            "python",
            "manage.py",
            "migrate",
            "--noinput",
        )
        compose(
            backend,
            "run",
            "--rm",
            "-T",
            "video_creator",
            "python",
            "manage.py",
            "collectstatic",
            "--noinput",
        )
        compose(
            backend,
            "run",
            "--rm",
            "-T",
            "video_creator",
            "python",
            "manage.py",
            "check",
            "--deploy",
        )
        compose(backend, "up", "-d", "--no-deps", "--force-recreate", *SERVICES)
        wait_http(public_url(backend))
        raw = compose(
            backend,
            "exec",
            "-T",
            "video_creator",
            "python",
            "-c",
            "import json; from video_creator.celery import app; print(json.dumps(app.control.inspect(timeout=10).ping()))",
            capture=True,
        )
        if len(json.loads(raw) or {}) < 2:
            raise RuntimeError("Both workers must respond after deployment")
    except Exception:
        print(
            "Release failed. Backups and release files retained; inspect the failed deployment before restoring data.",
            file=sys.stderr,
        )
        raise
    link = CURRENT.with_name(CURRENT.name + ".next")
    link.unlink(missing_ok=True)
    link.symlink_to(release, target_is_directory=True)
    link.replace(CURRENT)
    (STATE / ".deployed-sha").write_text(sha + "\n")
    print(f"Deployed {sha}; HTTPS API and both workers verified", flush=True)


def main():
    os.umask(0o077)
    os.environ["PATH"] = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    command = os.environ.get("SSH_ORIGINAL_COMMAND", "")
    if command == "status":
        print("Viddie restricted deployment endpoint is ready")
        return
    sha = release_sha(command)
    with Path("/run/viddie-deploy.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        deploy(sha, sys.stdin.buffer)


if __name__ == "__main__":
    main()
