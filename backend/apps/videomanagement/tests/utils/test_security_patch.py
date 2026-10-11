from importlib.metadata import distribution
from unittest.mock import patch

from django.test import SimpleTestCase

from basicsr.utils import dist_util
from scripts.patch_basicsr_security import SAFE, patch_source


class BasicSRSecurityPatchTests(SimpleTestCase):
    def test_installed_helper_has_the_security_patch(self):
        source = (
            distribution("basicsr")
            .locate_file("basicsr/utils/dist_util.py")
            .read_text()
        )
        self.assertIn(SAFE, source)
        self.assertEqual(patch_source(source), source)

    def test_slurm_host_list_is_passed_as_one_argument_without_a_shell(self):
        environment = {
            "SLURM_PROCID": "0",
            "SLURM_NTASKS": "2",
            "SLURM_NODELIST": "node-[01,02]",
        }
        with (
            patch.dict(dist_util.os.environ, environment, clear=True),
            patch.object(dist_util.torch.cuda, "device_count", return_value=1),
            patch.object(dist_util.torch.cuda, "set_device"),
            patch.object(dist_util.dist, "init_process_group"),
            patch.object(
                dist_util.subprocess, "check_output", return_value="node-01\nnode-02\n"
            ) as run,
        ):
            dist_util._init_dist_slurm("gloo")
            self.assertEqual(dist_util.os.environ["MASTER_ADDR"], "node-01")
        run.assert_called_once_with(
            ["scontrol", "show", "hostname", "node-[01,02]"], text=True
        )

    def test_shell_payloads_and_command_options_are_rejected(self):
        for host_list in (
            "node;touch /tmp/pwned",
            "$(id)",
            "node\nreboot",
            "--help",
            "",
        ):
            environment = {
                "SLURM_PROCID": "0",
                "SLURM_NTASKS": "1",
                "SLURM_NODELIST": host_list,
            }
            with (
                self.subTest(host_list=host_list),
                patch.dict(dist_util.os.environ, environment, clear=True),
                patch.object(dist_util.torch.cuda, "device_count", return_value=1),
                patch.object(dist_util.torch.cuda, "set_device"),
                patch.object(dist_util.subprocess, "check_output") as run,
                self.assertRaises(ValueError),
            ):
                dist_util._init_dist_slurm("gloo")
            run.assert_not_called()

    def test_unexpected_upstream_source_fails_closed(self):
        with self.assertRaises(RuntimeError):
            patch_source("# changed upstream source")
