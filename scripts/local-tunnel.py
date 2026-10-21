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
    lines = ENV.read_text().splitlines(keepends=True)
    for key in ("SOCIAL_PUBLIC_BASE_URL", "FRONTEND_URL"):
        pattern = re.compile(rf"^\s*(?:export\s+)?{key}\s*=")
        found = False
        for index, line in enumerate(lines):
            if pattern.match(line):
                lines[index] = f"{key}={url}\n"
                found = True
        if not found:
            if lines and not lines[-1].endswith("\n"):
                lines[-1] += "\n"
            lines.append(f"{key}={url}\n")
    ENV.write_text("".join(lines))


def reload_backend():
    subprocess.run(
        ["docker", "compose", "up", "-d", "--no-deps", "--no-build",
         "video_creator", "celery", "celery-beat"],
        cwd=ROOT / "backend", check=True, timeout=120,
    )


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

    with tunnel_lock() as acquired:
        if not acquired:
            raise RuntimeError("A managed tunnel is already running. Use status or stop.")
        stop_file = STATE / "stop"
        url_file = STATE / "url"
        stop_file.unlink(missing_ok=True)
        url_file.unlink(missing_ok=True)
        print("Exposing the local app and API on port 3000 through temporary public HTTPS.", flush=True)
        process = None
        try:
            log_path = STATE / "cloudflared.log"
            with log_path.open("w") as log:
                os.chmod(log_path, 0o600)
                process = subprocess.Popen(
                    ["cloudflared", "tunnel", "--url", "http://127.0.0.1:3000", "--no-autoupdate"],
                    stdout=log, stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
                deadline = time.monotonic() + 90
                url = None
                while process.poll() is None and not stop_file.exists():
                    match = URL_PATTERN.search(log_path.read_text(errors="replace"))
                    if match:
                        url = match.group()
                        break
                    if time.monotonic() > deadline:
                        raise RuntimeError(f"Timed out waiting for the public URL. Inspect {log_path}.")
                    time.sleep(0.25)
                if stop_file.exists():
                    return
                if not url or process.poll() is not None:
                    raise RuntimeError(f"Cloudflare did not start a tunnel. Inspect {log_path}.")
                original_env = ENV.read_text()
                update_origins(url)
                try:
                    reload_backend()
                except (OSError, subprocess.SubprocessError) as error:
                    ENV.write_text(original_env)
                    raise RuntimeError(
                        "Backend reload failed; backend/.env was restored. "
                        "Reload the backend and workers before continuing."
                    ) from error
                if process.poll() is not None:
                    raise RuntimeError("The tunnel stopped while reloading the backend. Start it again.")
                url_file.write_text(url + "\n")
                print(f"\nViddie: {url}\nUpdated backend/.env and reloaded the backend and workers.", flush=True)
                print("Update the callback URLs in your Google, TikTok and Meta developer dashboards:", flush=True)
                for platform in ("youtube", "tiktok", "instagram"):
                    print(f"  {platform}: {url}/api/publishing/oauth/{platform}/callback/", flush=True)
                print("\nKeep this terminal open. Press Ctrl+C, or run the stop command in another terminal.", flush=True)
                while process.poll() is None and not stop_file.exists():
                    time.sleep(0.25)
                if not stop_file.exists():
                    raise RuntimeError(f"The tunnel exited unexpectedly. Inspect {log_path}.")
        finally:
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            url_file.unlink(missing_ok=True)
            stop_file.unlink(missing_ok=True)
            print("Tunnel stopped. Docker containers are left running.", flush=True)


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
    parser.add_argument("action", choices=("start", "stop", "status"))
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
