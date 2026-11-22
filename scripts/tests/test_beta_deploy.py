import importlib.util
import io
import os
import textwrap
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "deploy_beta", Path(__file__).parents[1] / "deploy_beta.py"
)
deploy_beta = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy_beta)
REQUIRED = [
    "backend/manage.py",
    "backend/docker-compose.beta.yml",
    "backend/Dockerfile",
    "frontend/Dockerfile",
]
SHA = "a" * 40


def archive_bytes(extra=()):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz") as archive:
        for name, data, kind in [
            (name, b"x", tarfile.REGTYPE) for name in REQUIRED
        ] + list(extra):
            member = tarfile.TarInfo(name)
            member.type = kind
            member.size = len(data) if kind == tarfile.REGTYPE else 0
            member.linkname = "/etc/passwd" if kind == tarfile.SYMTYPE else ""
            archive.addfile(member, io.BytesIO(data) if member.isfile() else None)
    return output.getvalue()


class ArchiveTests(unittest.TestCase):
    def test_accepts_only_the_restricted_deploy_command(self):
        self.assertEqual(deploy_beta.release_sha("deploy " + SHA), SHA)
        for command in (
            "bash",
            "deploy main",
            "deploy " + SHA + "; id",
            "deploy ../main",
            "deploy " + SHA + "\n",
        ):
            with self.subTest(command=command), self.assertRaises(ValueError):
                deploy_beta.release_sha(command)

    def unpack(self, extra=()):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        archive = root / "release.tar.gz"
        archive.write_bytes(archive_bytes(extra))
        destination = root / "source"
        destination.mkdir()
        deploy_beta.unpack(archive, destination)
        return destination

    def test_extracts_source_and_allows_the_configuration_example(self):
        destination = self.unpack(
            [("backend/.env_example", b"EXAMPLE=true", tarfile.REGTYPE)]
        )
        self.assertEqual(
            (destination / "backend/.env_example").read_bytes(), b"EXAMPLE=true"
        )
        self.assertFalse((destination / "backend/.env").exists())

    def test_rejects_secrets_data_symlinks_and_path_traversal(self):
        for name, kind in [
            ("../escape", tarfile.REGTYPE),
            ("/etc/passwd", tarfile.REGTYPE),
            ("backend/.env", tarfile.REGTYPE),
            ("backend/media/output.mp4", tarfile.REGTYPE),
            ("backend/private-clips/video.mp4", tarfile.REGTYPE),
            ("backend/link", tarfile.SYMTYPE),
            (".git/config", tarfile.REGTYPE),
            ("backend/manage.py", tarfile.REGTYPE),
        ]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.unpack([(name, b"x", kind)])

    def test_limits_expanded_archive_size(self):
        with patch.object(deploy_beta, "MAX_CONTENT", 6), self.assertRaises(ValueError):
            self.unpack([("large", b"0123456789", tarfile.REGTYPE)])

    def test_limits_received_archive_size(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(deploy_beta, "MAX_ARCHIVE", 3),
        ):
            with self.assertRaises(ValueError):
                deploy_beta.receive(
                    io.BytesIO(b"0123456789"), Path(directory) / "archive"
                )

    def test_rejects_incomplete_application_archives(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "archive.tar.gz"
            with tarfile.open(archive, "w:gz"):
                pass
            with self.assertRaises(ValueError):
                deploy_beta.unpack(archive, root / "source")


class BranchPolicyTests(unittest.TestCase):
    def test_only_the_same_repository_develop_branch_can_target_main(self):
        source = (
            Path(__file__).parents[2] / ".github/workflows/branch-policy.yml"
        ).read_text()
        script = textwrap.dedent(
            source.split("        run: |\n", 1)[1].split("  release-tooling:", 1)[0]
        )
        for base, head, repository, allowed in [
            ("main", "develop", "owner/repo", True),
            ("main", "feature", "owner/repo", False),
            ("main", "develop", "fork/repo", False),
            ("develop", "feature", "owner/repo", True),
        ]:
            with self.subTest(base=base, head=head, repository=repository):
                result = subprocess.run(
                    ["bash", "-c", script],
                    capture_output=True,
                    env={
                        **os.environ,
                        "EVENT_NAME": "pull_request",
                        "BASE_REF": base,
                        "HEAD_REF": head,
                        "HEAD_REPO": repository,
                        "REPOSITORY": "owner/repo",
                    },
                )
                self.assertEqual(result.returncode == 0, allowed)


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name).resolve()
        self.state = self.root / "state"
        self.state.mkdir()
        (self.state / ".env").write_text("EXAMPLE=true\n")
        self.previous = self.root / "old"
        (self.previous / "backend").mkdir(parents=True)
        self.current = self.root / "current"
        self.current.symlink_to(self.previous)
        for name, value in [
            ("STATE", self.state),
            ("CURRENT", self.current),
            ("RELEASES", self.root / "releases"),
            ("BACKUPS", self.root / "backups"),
        ]:
            self.enterContext(patch.object(deploy_beta, name, value))
        self.calls = []
        self.failure = None
        self.enterContext(
            patch.object(deploy_beta, "compose", side_effect=self.compose)
        )
        self.http = self.enterContext(patch.object(deploy_beta, "wait_http"))

    def compose(self, backend, *args, capture=False, output=None):
        self.calls.append(args)
        if args[0] == "build":
            for directory in deploy_beta.DATA_DIRS:
                self.assertTrue((backend / directory).is_dir())
                self.assertTrue((self.state / directory).is_dir())
        if self.failure and self.failure in args:
            raise subprocess.CalledProcessError(1, args)
        if output:
            output.write(b"verified-database-backup")
        if capture:
            if deploy_beta.WORKER_CHECK in args:
                return "[0, 0, 0, 0]"
            if "settings.FRONTEND_URL" in args[-1]:
                return "https://video.example\n"
            return '{"general": {"ok": "pong"}, "renders": {"ok": "pong"}}'

    def test_deploys_with_a_backup_and_health_checks_before_changing_the_pointer(self):
        deploy_beta.deploy(SHA, io.BytesIO(archive_bytes()))
        self.assertNotEqual(self.current.resolve(), self.previous)
        self.assertEqual((self.state / ".deployed-sha").read_text().strip(), SHA)
        self.assertEqual(
            next((self.root / "backups").glob("*/database.dump")).read_bytes(),
            b"verified-database-backup",
        )
        self.assertEqual((self.current / "backend/.env").resolve(), self.state / ".env")
        self.http.assert_called_once_with("https://video.example")

    def test_build_failure_leaves_running_services_and_the_current_release_untouched(
        self,
    ):
        self.failure = "build"
        with self.assertRaises(subprocess.CalledProcessError):
            deploy_beta.deploy(SHA, io.BytesIO(archive_bytes()))
        self.assertEqual(self.current.resolve(), self.previous)
        self.assertFalse(any(call[0] == "stop" for call in self.calls))

    def test_migration_failure_keeps_backups_and_does_not_restore_old_code_over_a_changed_schema(
        self,
    ):
        self.failure = "migrate"
        with self.assertRaises(subprocess.CalledProcessError):
            deploy_beta.deploy(SHA, io.BytesIO(archive_bytes()))
        self.assertEqual(self.current.resolve(), self.previous)
        self.assertTrue(list((self.root / "backups").glob("*/database.dump")))
        self.assertFalse(any(call[0] in {"up", "start"} for call in self.calls))
        self.assertFalse((self.state / ".deployed-sha").exists())

    def test_container_startup_failure_keeps_the_previous_release_running(self):
        self.failure = "pass"
        with self.assertRaises(subprocess.CalledProcessError):
            deploy_beta.deploy(SHA, io.BytesIO(archive_bytes()))
        self.assertEqual(self.current.resolve(), self.previous)
        self.assertFalse(any(call[0] == "stop" for call in self.calls))
        self.assertFalse(any("migrate" in call for call in self.calls))

    def test_jobs_that_cannot_drain_restore_the_previous_api_and_scheduler(self):
        with patch.object(deploy_beta, "wait_idle", side_effect=TimeoutError):
            with self.assertRaises(TimeoutError):
                deploy_beta.deploy(SHA, io.BytesIO(archive_bytes()))
        self.assertIn(("start", "video_creator", "celery-beat"), self.calls)
        self.assertFalse(any("migrate" in call for call in self.calls))

    def test_duplicate_success_events_do_not_restart_a_healthy_revision(self):
        deploy_beta.deploy(SHA, io.BytesIO(archive_bytes()))
        stops = sum(call[0] == "stop" for call in self.calls)
        deploy_beta.deploy(SHA, io.BytesIO(archive_bytes()))
        self.assertEqual(sum(call[0] == "stop" for call in self.calls), stops)

    def test_backup_failure_restarts_existing_containers_before_any_schema_change(self):
        self.failure = 'pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB"'
        with self.assertRaises(subprocess.CalledProcessError):
            deploy_beta.deploy(SHA, io.BytesIO(archive_bytes()))
        self.assertIn(
            ("start", "video_creator", "celery", "celery-render", "celery-beat"),
            self.calls,
        )
        self.assertFalse(any("migrate" in call for call in self.calls))


if __name__ == "__main__":
    unittest.main()
