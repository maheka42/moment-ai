"""Unit tests for file ingestion helpers."""
import unittest

from fastapi import HTTPException

from backend.app.services.ingestion import extract_text_file, get_file_extension


class IngestionTests(unittest.TestCase):
    def test_extension_is_lowercase(self):
        self.assertEqual(get_file_extension("Lecture.PDF"), ".pdf")

    def test_extract_utf8_text(self):
        self.assertEqual(extract_text_file(b"  MOMENT AI notes  "), "MOMENT AI notes")

    def test_extract_utf8_bom_text(self):
        self.assertEqual(extract_text_file(b"\xef\xbb\xbfHello"), "Hello")

    def test_reject_empty_text(self):
        with self.assertRaises(HTTPException) as error:
            extract_text_file(b"   ")
        self.assertEqual(error.exception.status_code, 422)

    def test_reject_invalid_utf8(self):
        with self.assertRaises(HTTPException) as error:
            extract_text_file(b"\xff\xfe")
        self.assertEqual(error.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
