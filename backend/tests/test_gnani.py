"""Unit tests for Gnani REST, Batch STT, and Timbre adapters."""
import json
import unittest
from unittest.mock import Mock, patch

from backend.app.gnani import GnaniAPIError, GnaniClient


class GnaniAdapterTests(unittest.TestCase):
    def setUp(self):
        self.client = GnaniClient(
            api_key_id="test-key",
            stt_endpoint="https://api.vachana.ai/stt/v3",
            tts_endpoint="https://api.vachana.ai/api/v1/tts/inference",
        )

    @patch("backend.app.gnani.requests.post")
    def test_transcribes_audio_with_prisma_v3(self, post):
        response = Mock()
        response.ok = True
        response.status_code = 200
        response.json.return_value = {
            "success": True, "request_id": "req-test", "transcript": "नमस्ते",
            "model": "prisma-v3.0", "detected_language_code": "hi-IN",
        }
        post.return_value = response
        result = self.client.transcribe_with_prisma(b"fake-audio", "sample.wav")
        self.assertEqual(result["transcript"], "नमस्ते")
        args, kwargs = post.call_args
        self.assertEqual(args[0], "https://api.vachana.ai/stt/v3")
        self.assertEqual(kwargs["headers"]["X-API-Key-ID"], "test-key")
        self.assertEqual(kwargs["data"]["model"], "prisma-v3.0")
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
        response.json.return_value = {"detail": {"error_code": "INVALID_API_KEY", "message": "Unauthorized"}}
        post.return_value = response
        with self.assertRaises(GnaniAPIError) as error:
            self.client.transcribe_with_prisma(b"audio", "sample.wav")
        self.assertEqual(error.exception.status_code, 401)
        self.assertEqual(error.exception.error_type, "INVALID_API_KEY")

    @patch("backend.app.gnani.requests.post")
    def test_creates_and_uploads_batch_job(self, post):
        response = Mock()
        response.ok = True
        response.status_code = 201
        response.json.return_value = {"job_id": "job-123", "status": "CREATED"}
        post.return_value = response
        result = self.client.create_batch_job(b"audio-bytes", "lecture.wav", "en-IN")
        self.assertEqual(result["job_id"], "job-123")
        args, kwargs = post.call_args
        self.assertTrue(args[0].endswith("/stt/v3/batch/jobs"))
        self.assertEqual(kwargs["headers"]["X-API-Key-ID"], "test-key")
        config = kwargs["files"]["config"][1]
        self.assertEqual(json.loads(config)["model"], "gnani-prisma-v2.5")
        self.assertEqual(kwargs["files"]["files"][0], "lecture.wav")

    @patch("backend.app.gnani.requests.post")
    def test_timbre_returns_mp3_bytes(self, post):
        response = Mock()
        response.ok = True
        response.content = b"ID3-fake-mp3"
        post.return_value = response
        audio = self.client.synthesize_with_timbre("Hello", container="mp3")
        self.assertEqual(audio, b"ID3-fake-mp3")
        kwargs = post.call_args.kwargs
        self.assertEqual(kwargs["json"]["model"], "timbre-v2.5")
        self.assertEqual(kwargs["json"]["audio_config"]["container"], "mp3")
        self.assertEqual(kwargs["json"]["voice"], "Nalini")

    @patch("backend.app.gnani.requests.get")
    def test_downloads_batch_transcript(self, get):
        response = Mock()
        response.ok = True
        response.json.return_value = {"full_transcript": "Lecture text", "segments": []}
        get.return_value = response
        result = self.client.download_batch_transcript("https://files.example.com/transcript.json")
        self.assertEqual(result["full_transcript"], "Lecture text")
        get.assert_called_once()

    def test_rejects_non_https_transcript_url(self):
        with self.assertRaises(ValueError):
            self.client.download_batch_transcript("http://example.com/transcript.json")

    @patch("backend.app.gnani.requests.post")
    def test_calls_configured_hosted_llm_chat_completions_endpoint(self, post):
        response = Mock()
        response.ok = True
        response.status_code = 200
        response.json.return_value = {
            "choices": [{"message": {"content": '{"title": "Notes"}'}}]
        }
        post.return_value = response
        self.client.llm_endpoint = "https://api.groq.com/openai/v1/chat/completions"
        self.client.llm_api_key = "runtime-token"
        generated = self.client.generate_with_llm("Create study notes.")
        self.assertEqual(generated, '{"title": "Notes"}')
        kwargs = post.call_args.kwargs
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer runtime-token")
        self.assertEqual(kwargs["json"]["model"], self.client.llm_model)
        self.assertEqual(kwargs["json"]["max_completion_tokens"], 5000)

    def test_llm_requires_a_configured_endpoint(self):
        with self.assertRaises(RuntimeError):
            self.client.generate_with_llm("Generate notes.")


if __name__ == "__main__":
    unittest.main()
