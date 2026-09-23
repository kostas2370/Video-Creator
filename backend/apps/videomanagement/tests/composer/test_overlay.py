"""Burning a clip title into footage with ffmpeg."""

import os
import shutil
import tempfile
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from ...utils.composer import overlay
from ...utils.composer.overlay import add_text_to_video


def a_run(returncode=0, stderr=""):
    return MagicMock(returncode=returncode, stderr=stderr)


class AddTextToVideoTests(SimpleTestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="overlay-")
        self.addCleanup(shutil.rmtree, self.dir, True)

        self.video = os.path.join(self.dir, "clip.mp4")
        open(self.video, "w").close()

    def filtergraph(self, run):
        command = run.call_args.args[0]
        return command[command.index("-vf") + 1]

    def test_returns_the_new_file_and_drops_the_original(self):
        with patch.object(overlay.subprocess, "run", return_value=a_run()):
            output = add_text_to_video(self.video, "a title")

        self.assertTrue(output.endswith(".mp4"))
        self.assertFalse(os.path.exists(self.video))

    def test_hands_the_title_to_ffmpeg_as_a_file_rather_than_inline(self):
        hostile = "it's 3:00 — drop\\table"

        with patch.object(overlay.subprocess, "run", return_value=a_run()) as run:
            add_text_to_video(self.video, hostile)

        graph = self.filtergraph(run)
        self.assertIn("textfile=", graph)
        self.assertNotIn(hostile, graph)

    def test_cleans_up_the_text_file_it_wrote(self):
        with patch.object(overlay.subprocess, "run", return_value=a_run()) as run:
            add_text_to_video(self.video, "a title")

        graph = self.filtergraph(run)
        text_path = graph.split("textfile=")[1].split(":")[0]

        self.assertFalse(os.path.exists(text_path))

    def test_keeps_the_original_when_ffmpeg_fails(self):
        with patch.object(
            overlay.subprocess, "run", return_value=a_run(1, "bad codec")
        ):
            self.assertEqual(add_text_to_video(self.video, "a title"), "")

        self.assertTrue(os.path.exists(self.video))
