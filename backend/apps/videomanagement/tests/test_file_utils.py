import os
import tempfile

from django.test import SimpleTestCase

from ..utils.file_utils import check_which_file_exists, generate_directory


class GenerateDirectoryTests(SimpleTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def path(self, *parts):
        return os.path.join(self.tmp.name, *parts)

    def test_creates_the_directory_with_the_subfolders_the_pipeline_writes_into(self):
        created = generate_directory(self.path("a-video"))

        self.assertEqual(created, self.path("a-video"))
        self.assertTrue(os.path.isdir(os.path.join(created, "dialogues")))
        self.assertTrue(os.path.isdir(os.path.join(created, "images")))

    def test_suffixes_the_name_rather_than_reusing_an_existing_directory(self):
        first = generate_directory(self.path("a-video"))
        second = generate_directory(self.path("a-video"))

        self.assertNotEqual(first, second)
        self.assertEqual(second, self.path("a-video 1"))

    def test_keeps_counting_past_the_first_collision(self):
        for _ in range(3):
            generate_directory(self.path("a-video"))

        self.assertEqual(
            generate_directory(self.path("a-video")), self.path("a-video 3")
        )


class CheckWhichFileExistsTests(SimpleTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_returns_the_first_path_that_is_on_disk(self):
        present = os.path.join(self.tmp.name, "there.png")
        open(present, "w").close()

        found = check_which_file_exists(
            [os.path.join(self.tmp.name, "missing.png"), present]
        )

        self.assertEqual(found, present)

    def test_returns_none_when_nothing_is_on_disk(self):
        self.assertIsNone(check_which_file_exists([os.path.join(self.tmp.name, "x")]))

    def test_returns_none_for_an_empty_list(self):
        self.assertIsNone(check_which_file_exists([]))
