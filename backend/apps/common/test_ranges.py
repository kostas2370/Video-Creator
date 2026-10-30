from django.test import SimpleTestCase

from .ranges import parse_byte_range


class ByteRangeTests(SimpleTestCase):
    def test_absent_range_including_an_empty_file(self):
        for header in (None, ""):
            for size in (0, 8):
                self.assertIsNone(parse_byte_range(header, size))

    def test_parses_closed_open_and_suffix_ranges(self):
        for header, expected in (
            ("bytes=1-3", (1, 3)),
            ("bytes=0-0", (0, 0)),
            ("bytes=5-", (5, 7)),
            ("bytes=-3", (5, 7)),
            ("bytes=6-999", (6, 7)),
            ("bytes=-999", (0, 7)),
            ("bytes=0-7", (0, 7)),
            (" bytes=1-3 ", (1, 3)),
        ):
            with self.subTest(header=header):
                self.assertEqual(parse_byte_range(header, 8), expected)

    def test_rejects_invalid_unsatisfiable_and_multiple_ranges(self):
        for header in (
            "bytes=",
            "bytes=-",
            "bytes=-0",
            "bytes=8-",
            "bytes=5-2",
            "bytes=0-1,3-4",
            "items=0-1",
            "bytes=one-two",
            "bytes=١-٣",
            "bytes=" + "9" * 10000 + "-",
        ):
            with self.subTest(header=header[:50]), self.assertRaises(ValueError):
                parse_byte_range(header, 8)

    def test_no_range_is_satisfiable_for_an_empty_file(self):
        for header in ("bytes=0-0", "bytes=0-", "bytes=-1"):
            with self.subTest(header=header), self.assertRaises(ValueError):
                parse_byte_range(header, 0)
