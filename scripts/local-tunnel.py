#!/usr/bin/env python3
"""Manage a foreground Cloudflare Quick Tunnel for the local Docker app (macOS/Linux)."""

import argparse
import contextlib
import fcntl
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "backend" / ".local-tunnel"
ENV = ROOT / "backend" / ".env"
URL_PATTERN = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com\b")


@contextlib.contextmanager
def tunnel_lock():
    STATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (STATE / "lock").open("a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield False
        else:
            try:
                yield True
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)


def update_origins(url):
    """Keep credentials, comments and unrelated configuration unchanged."""
    content = ENV.read_text()
    for key in ("SOCIAL_PUBLIC_BASE_URL", "FRONTEND_URL"):
        content, count = re.subn(
            rf"(?m)^[ \t]*(?:export[ \t]+)?{key}[ \t]*=[^\r\n]*",
            f"{key}={url}", content,
        )
        if not count:
            if content and not content.endswith("\n"):
                content += "\n"
            content += f"{key}={url}\n"
    ENV.write_text(content)


def reload_backend():
    subprocess.run(
        ["docker", "compose", "up", "-d", "--no-deps", "--no-build",
         "video_creator", "celery", "celery-beat"],
        cwd=ROOT / "backend", check=True, timeout=120,
    )


@contextlib.contextmanager
def tunnel_session():
    """Own the lock, child process and runtime files for one tunnel."""
    with tunnel_lock() as acquired:
        if not acquired:
            raise RuntimeError("A managed tunnel is already running. Use status or stop.")
        for name in ("stop", "url"):
            (STATE / name).unlink(missing_ok=True)
        log_path = STATE / "cloudflared.log"
        with log_path.open("w") as log:
            os.chmod(log_path, 0o600)
            process = subprocess.Popen(
                ["cloudflared", "tunnel", "--url", "http://127.0.0.1:3000", "--no-autoupdate"],
                stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
            )
            try:
                yield process
            finally:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                for name in ("url", "stop"):
                    (STATE / name).unlink(missing_ok=True)
                print("Tunnel stopped. Docker containers are left running.", flush=True)


def wait_for_url(process):
    """Return the public URL, or None when stop is requested during startup."""
    deadline = time.monotonic() + 90
    log_path = STATE / "cloudflared.log"
    while not (STATE / "stop").exists():
        if process.poll() is not None:
            raise RuntimeError(f"Cloudflare did not start a tunnel. Inspect {log_path}.")
        match = URL_PATTERN.search(log_path.read_text(errors="replace"))
        if match:
            return match.group()
        if time.monotonic() > deadline:
            raise RuntimeError(f"Timed out waiting for the public URL. Inspect {log_path}.")
        time.sleep(0.25)
    return None


def start():
    for command in ("cloudflared", "docker"):
        if not shutil.which(command):
            raise RuntimeError(f"Install {command} before starting the tunnel.")
    if not ENV.is_file():
        raise RuntimeError("Create backend/.env before starting the tunnel.")
    try:
        with urllib.request.urlopen("http://127.0.0.1:3000/", timeout=5):
            pass
    except urllib.error.HTTPError:
        pass  # An HTTP response still confirms the local server is running.
    except urllib.error.URLError as error:
        raise RuntimeError("Start the Docker app on port 3000 first.") from error

    with tunnel_session() as process:
        print("Exposing the local app and API on port 3000 through temporary public HTTPS.", flush=True)
        url = wait_for_url(process)
        if url is None:
            return
        original_env = ENV.read_text()
        try:
            update_origins(url)
            reload_backend()
        except (OSError, subprocess.SubprocessError) as error:
            ENV.write_text(original_env)
            raise RuntimeError(
                "Backend reload failed; backend/.env was restored. "
                "Reload the backend and workers before continuing."
            ) from error
        if (STATE / "stop").exists():
            return
        if process.poll() is not None:
            raise RuntimeError("The tunnel stopped while reloading the backend. Start it again.")
        (STATE / "url").write_text(url + "\n")
        print(f"\nViddie: {url}\nUpdated backend/.env and reloaded the backend and workers.", flush=True)
        print("Update the callback URLs in your Google, TikTok and Meta developer dashboards:", flush=True)
        for platform in ("youtube", "tiktok", "instagram"):
            print(f"  {platform}: {url}/api/publishing/oauth/{platform}/callback/", flush=True)
        print("\nKeep this terminal open. Press Ctrl+C, or run the stop command in another terminal.", flush=True)
        while not (STATE / "stop").exists():
            if process.poll() is not None:
                raise RuntimeError(f"The tunnel exited unexpectedly. Inspect {STATE / 'cloudflared.log'}.")
            time.sleep(0.25)


def status():
    with tunnel_lock() as acquired:
        if acquired:
            print("No managed tunnel is running.")
        else:
            url_file = STATE / "url"
            print(f"Tunnel running: {url_file.read_text().strip()}" if url_file.exists()
                  else "Tunnel is starting or stopping.")


def stop():
    with tunnel_lock() as acquired:
        if acquired:
            print("No managed tunnel is running.")
            return
        (STATE / "stop").touch()
    deadline = time.monotonic() + 135  # Allow an in-progress Compose reload to finish.
    while time.monotonic() < deadline:
        with tunnel_lock() as acquired:
            if acquired:
                print("Tunnel stopped. Docker containers are left running.")
                return
        time.sleep(0.25)
    raise RuntimeError("Stop is still pending. Press Ctrl+C in the tunnel's terminal.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", default="start", choices=("start", "stop", "status"))
    args = parser.parse_args()
    if args.action == "start":
        def interrupt(_signum, _frame):
            raise KeyboardInterrupt

        # Closing the terminal or terminating the wrapper must also close public access.
        signal.signal(signal.SIGTERM, interrupt)
        signal.signal(signal.SIGHUP, interrupt)
    try:
        {"start": start, "stop": stop, "status": status}[args.action]()
    except KeyboardInterrupt:
        print("Tunnel stopped.")
    except (RuntimeError, OSError, subprocess.SubprocessError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
