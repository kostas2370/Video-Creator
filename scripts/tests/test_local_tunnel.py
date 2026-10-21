"""Lifecycle checks using a fake cloudflared process; no public network access."""

import contextlib
import importlib.util
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("local_tunnel", Path(__file__).parents[1] / "local-tunnel.py")
tunnel = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tunnel)


class TunnelTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        (self.root / "backend").mkdir()
        self.env = self.root / "backend" / ".env"
        self.original = "# Keep this comment\nSECRET=keep-me\nexport FRONTEND_URL = https://old.example\n"
        self.env.write_text(self.original)
        self.patches = patch.multiple(tunnel, ROOT=self.root, ENV=self.env,
                                      STATE=self.root / "backend" / ".local-tunnel")
        self.patches.start()
        self.addCleanup(self.directory.cleanup)
        self.addCleanup(self.patches.stop)

    def test_origin_updates_preserve_other_values_and_replace_exported_keys(self):
        tunnel.update_origins("https://test.trycloudflare.com")
        tunnel.update_origins("https://second.trycloudflare.com")
        content = self.env.read_text()
        self.assertIn("# Keep this comment\nSECRET=keep-me\n", content)
        self.assertEqual(content.count("FRONTEND_URL="), 1)
        self.assertEqual(content.count("SOCIAL_PUBLIC_BASE_URL="), 1)
        self.assertNotIn("old.example", content)
        self.assertNotIn("https://test.trycloudflare.com", content)

    def fake_child(self, command, **kwargs):
        code = "import time; print('https://test.trycloudflare.com', flush=True); time.sleep(30)"
        self.child = self.real_popen([sys.executable, "-c", code], **kwargs)
        self.addCleanup(lambda: self.child.poll() is None and self.child.kill())
        return self.child

    def test_start_status_stop_and_duplicate_start(self):
        self.real_popen = subprocess.Popen
        failures = []

        def run():
            try:
                tunnel.start()
            except Exception as error:
                failures.append(error)

        output = io.StringIO()
        with contextlib.redirect_stdout(output), patch.object(tunnel.shutil, "which", return_value="fake"), \
                patch.object(tunnel.urllib.request, "urlopen"), \
                patch.object(tunnel.subprocess, "Popen", side_effect=self.fake_child), \
                patch.object(tunnel, "reload_backend") as reload:
            worker = threading.Thread(target=run)
            worker.start()
            try:
                deadline = time.monotonic() + 5
                while not (tunnel.STATE / "url").exists() and time.monotonic() < deadline:
                    time.sleep(0.02)
                self.assertTrue((tunnel.STATE / "url").exists())
                tunnel.status()
                with self.assertRaisesRegex(RuntimeError, "already running"):
                    tunnel.start()
                tunnel.stop()
            finally:
                if worker.is_alive():
                    (tunnel.STATE / "stop").touch()
                worker.join(timeout=5)
            self.assertFalse(worker.is_alive())
            self.assertEqual(failures, [])
            reload.assert_called_once()
        self.assertIn("Tunnel running: https://test.trycloudflare.com", output.getvalue())
        self.assertIsNotNone(self.child.poll())
        self.assertFalse((tunnel.STATE / "url").exists())
        self.assertIn("SOCIAL_PUBLIC_BASE_URL=https://test.trycloudflare.com", self.env.read_text())

    def test_failed_reload_restores_config_and_stops_child(self):
        self.real_popen = subprocess.Popen
        with contextlib.redirect_stdout(io.StringIO()), patch.object(tunnel.shutil, "which", return_value="fake"), \
                patch.object(tunnel.urllib.request, "urlopen"), \
                patch.object(tunnel.subprocess, "Popen", side_effect=self.fake_child), \
                patch.object(tunnel, "reload_backend", side_effect=subprocess.CalledProcessError(1, "docker")):
            with self.assertRaisesRegex(RuntimeError, "was restored"):
                tunnel.start()
        self.assertEqual(self.env.read_text(), self.original)
        self.assertIsNotNone(self.child.poll())
        self.assertFalse((tunnel.STATE / "url").exists())
        with tunnel.tunnel_lock() as acquired:
            self.assertTrue(acquired)

    def test_idle_stop_does_not_signal_any_process(self):
        with patch.object(tunnel.subprocess, "Popen") as process, contextlib.redirect_stdout(io.StringIO()):
            tunnel.stop()
            tunnel.status()
        process.assert_not_called()
        self.assertEqual(self.env.read_text(), self.original)


if __name__ == "__main__":
    unittest.main()
