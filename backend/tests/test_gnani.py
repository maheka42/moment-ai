"""Tests for the Gnani Prisma v3 REST adapter."""
import unittest
from unittest.mock import Mock, patch

from backend.app.gnani import GnaniAPIError, GnaniClient


class PrismaAdapterTests(unittest.TestCase):
    def setUp(self):
        self.client = GnaniClient(
            api_key_id="test-key",
            stt_endpoint="https://api.vachana.ai/stt/v3",
        )

    @patch("backend.app.gnani.requests.post")
    def test_transcribes_audio_with_prisma_v3(self, post):
        response = Mock()
        response.ok = True
        response.json.return_value = {
            "success": True,
            "request_id": "req-test",
            "transcript": "नमस्ते",
            "model": "prisma-v3.0",
            "detected_language_code": "hi-IN",
        }
        post.return_value = response

        result = self.client.transcribe_with_prisma(
            b"fake-audio",
            "sample.wav",
            language_code="indic-auto",
            output_format="transcribe",
        )

        self.assertEqual(result["transcript"], "नमस्ते")
        args, kwargs = post.call_args
        self.assertEqual(args[0], "https://api.vachana.ai/stt/v3")
        self.assertEqual(kwargs["headers"]["X-API-Key-ID"], "test-key")
        self.assertEqual(kwargs["data"]["model"], "prisma-v3.0")
        self.assertEqual(kwargs["data"]["language_code"], "indic-auto")
        self.assertEqual(kwargs["files"]["audio_file"][0], "sample.wav")

    def test_missing_api_key_is_rejected(self):
        client = GnaniClient(stt_endpoint="https://api.vachana.ai/stt/v3")
        with self.assertRaises(RuntimeError):
            client.transcribe_with_prisma(b"audio", "sample.wav")

    def test_empty_audio_is_rejected(self):
        with self.assertRaises(ValueError):
            self.client.transcribe_with_prisma(b"", "sample.wav")

    @patch("backend.app.gnani.requests.post")
    def test_provider_error_is_normalized(self, post):
        response = Mock()
        response.ok = False
        response.status_code = 401
        response.json.return_value = {
            "detail": {"error_code": "INVALID_API_KEY", "message": "Unauthorized"}
        }
        post.return_value = response

        with self.assertRaises(GnaniAPIError) as error:
            self.client.transcribe_with_prisma(b"audio", "sample.wav")

        self.assertEqual(error.exception.status_code, 401)
        self.assertEqual(error.exception.error_type, "INVALID_API_KEY")


if __name__ == "__main__":
    unittest.main()
