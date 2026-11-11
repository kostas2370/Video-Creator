import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class MusicCatalogStartupTests(unittest.TestCase):
    def run_script(self, script, enabled=None):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "work").mkdir()
            (root / "src").mkdir()
            binary = root / "bin"
            binary.mkdir()
            calls = root / "calls.txt"
            for executable in ("python", "uvicorn"):
                stub = binary / executable
                stub.write_text(
                    f'#!/bin/sh\nprintf "%s\\n" "{executable} $*" >> "$CATALOG_TEST_CALLS"\n'
                )
                stub.chmod(0o755)
            env = {
                **os.environ,
                "PATH": str(binary) + os.pathsep + os.environ["PATH"],
                "CATALOG_TEST_CALLS": str(calls),
            }
            env.pop("MUSIC_CATALOG_AUTO_SETUP", None)
            if enabled is not None:
                env["MUSIC_CATALOG_AUTO_SETUP"] = enabled
            subprocess.run(
                ["bash", str(ROOT / "backend/scripts" / script)],
                cwd=root / "work",
                env=env,
                capture_output=True,
                text=True,
                check=True,
            )
            return calls.read_text().splitlines()

    def test_both_setup_paths_import_after_migrations_by_default(self):
        for script in ("startdjango.sh", "setupdjango.sh"):
            with self.subTest(script=script):
                calls = self.run_script(script)
                importer = "python manage.py setup_music_catalog --best-effort"
                self.assertEqual(calls.count(importer), 1)
                self.assertLess(
                    calls.index("python manage.py migrate"), calls.index(importer)
                )
                if script == "startdjango.sh":
                    self.assertTrue(calls[-1].startswith("uvicorn "))
                    self.assertLess(calls.index(importer), len(calls) - 1)

    def test_automatic_import_can_be_disabled_for_both_setup_paths(self):
        for script in ("startdjango.sh", "setupdjango.sh"):
            with self.subTest(script=script):
                calls = self.run_script(script, enabled="false")
                self.assertFalse(
                    any("setup_music_catalog" in command for command in calls)
                )


if __name__ == "__main__":
    unittest.main()
