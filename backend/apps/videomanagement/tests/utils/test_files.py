import os
import tempfile
from types import SimpleNamespace

from django.core.exceptions import SuspiciousFileOperation
from django.test import SimpleTestCase

from ...utils.file_utils import (
    check_if_image,
    check_if_video,
    check_which_file_exists,
    generate_directory,
    stored_file_exists,
)


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


class FileTypeTests(SimpleTestCase):
    def test_recognises_stills_by_extension_whatever_the_case(self):
        for path in ("a.jpg", "a.JPEG", "a/b.PNG"):
            with self.subTest(path=path):
                self.assertTrue(check_if_image(path))
                self.assertFalse(check_if_video(path))

    def test_recognises_footage_by_extension(self):
        for path in ("a.mp4", "a/b.AVI"):
            with self.subTest(path=path):
                self.assertTrue(check_if_video(path))
                self.assertFalse(check_if_image(path))

    def test_recognises_neither_for_anything_else(self):
        self.assertFalse(check_if_image("a.wav"))
        self.assertFalse(check_if_video("a.wav"))


class StoredFileExistsTests(SimpleTestCase):
    def test_an_empty_field_has_nothing_behind_it(self):
        self.assertFalse(stored_file_exists(None))
        self.assertFalse(stored_file_exists(""))

    def test_a_path_outside_the_media_root_counts_as_missing(self):
        class Refuses(SimpleNamespace):
            @property
            def path(self):
                raise SuspiciousFileOperation("outside the base path")

        self.assertFalse(stored_file_exists(Refuses()))

    def test_a_field_with_no_file_behind_it_counts_as_missing(self):
        class Unset(SimpleNamespace):
            @property
            def path(self):
                raise ValueError("no file associated")

        self.assertFalse(stored_file_exists(Unset()))
