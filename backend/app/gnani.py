"""Gnani API adapters based on the published API contracts."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests


class GnaniAPIError(RuntimeError):
    """Safe, user-displayable error returned by a Gnani API request."""

    def __init__(self, status_code: int, message: str, error_type: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.error_type = error_type


@dataclass
class GnaniClient:
    base_url: str = "https://api.vachana.ai"
    api_key_id: str | None = None
    stt_endpoint: str | None = None
    prisma_model: str | None = "prisma-v3.0"
    tts_endpoint: str | None = None
    batch_stt_model: str = "gnani-prisma-v2.5"
    llm_endpoint: str | None = None
    llm_api_key: str | None = None
    llm_model: str = "openai/gpt-oss-120b"

    @classmethod
    def from_env(cls) -> "GnaniClient":
        base_url = os.getenv("GNANI_BASE_URL", "https://api.vachana.ai").rstrip("/")
        return cls(
            base_url=base_url,
            api_key_id=os.getenv("GNANI_API_KEY_ID"),
            stt_endpoint=os.getenv("GNANI_STT_ENDPOINT", f"{base_url}/stt/v3"),
            prisma_model=os.getenv("GNANI_PRISMA_MODEL", "prisma-v3.0").strip() or None,
            tts_endpoint=os.getenv("GNANI_TTS_ENDPOINT") or f"{base_url}/api/v1/tts/inference",
            batch_stt_model=os.getenv(
                "GNANI_BATCH_STT_MODEL", "gnani-prisma-v2.5"
            ),
            llm_endpoint=os.getenv("LLM_API_URL") or None,
            llm_api_key=os.getenv("LLM_API_KEY") or None,
            llm_model=os.getenv("LLM_MODEL", "openai/gpt-oss-120b"),
        )

    def auth_headers(self) -> dict[str, str]:
        if not self.api_key_id:
            raise RuntimeError("Configure GNANI_API_KEY_ID in your local .env file.")
        return {"X-API-Key-ID": self.api_key_id}

    @staticmethod
    def _raise_provider_error(response: requests.Response, fallback: str) -> None:
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        error = payload.get("error", {}) if isinstance(payload, dict) else {}
        detail = payload.get("detail", {}) if isinstance(payload, dict) else {}
        message = (
            error.get("message") if isinstance(error, dict) else None
        ) or (
            detail.get("message") if isinstance(detail, dict) else None
        ) or (
            payload.get("message") if isinstance(payload, dict) else None
        ) or fallback
        error_type = (
            error.get("type") if isinstance(error, dict) else None
        ) or (
            detail.get("error_code") if isinstance(detail, dict) else None
        ) or (
            payload.get("error") if isinstance(payload, dict) and isinstance(payload.get("error"), str) else None
        )
        raise GnaniAPIError(response.status_code, message, error_type)

    @staticmethod
    def _json_response(response: requests.Response, fallback: str) -> dict[str, Any]:
        if not response.ok:
            GnaniClient._raise_provider_error(response, fallback)
        try:
            payload = response.json()
        except ValueError as exc:
            raise GnaniAPIError(response.status_code, "Provider returned invalid JSON.") from exc
        if not isinstance(payload, dict):
            raise GnaniAPIError(502, "Provider returned an unexpected response format.")
        return payload

    def transcribe_with_prisma(
        self,
        audio_bytes: bytes,
        filename: str,
        language_code: str = "indic-auto",
        output_format: str = "transcribe",
        topic: str | None = None,
        keyterms: list[str] | None = None,
        previous_text: str | None = None,
        speaker_names: list[str] | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """Call the Prisma v3.0 short-clip REST endpoint."""
        if not audio_bytes:
            raise ValueError("Audio file is empty.")
        if not self.stt_endpoint:
            raise RuntimeError("Configure GNANI_STT_ENDPOINT in your local .env file.")
        if output_format not in {"verbatim", "transcribe", "codemix", "transliterate"}:
            raise ValueError("Unsupported Prisma v3.0 output format.")
        if not language_code and output_format != "transliterate":
            raise ValueError("language_code is required unless format is transliterate.")

        fields: dict[str, str] = {"format": output_format}
        if self.prisma_model:
            fields["model"] = self.prisma_model
        if language_code:
            fields["language_code"] = language_code
        if topic:
            fields["topic"] = topic[:1600]
        if keyterms:
            fields["keyterms"] = json.dumps(keyterms[:200], ensure_ascii=False)
        if previous_text:
            fields["previous_text"] = previous_text[-600:]
        if speaker_names:
            fields["speaker_names"] = json.dumps(speaker_names[:4], ensure_ascii=False)

        headers = self.auth_headers()
        if request_id:
            headers["X-API-Request-ID"] = request_id
        mime_types = {
            ".wav": "audio/wav", ".mp3": "audio/mpeg", ".ogg": "audio/ogg",
            ".flac": "audio/flac", ".aac": "audio/aac", ".m4a": "audio/mp4",
        }
        suffix = Path(filename).suffix.lower()
        try:
            response = requests.post(
                self.stt_endpoint,
                headers=headers,
                files={"audio_file": (Path(filename).name, audio_bytes, mime_types.get(suffix, "application/octet-stream"))},
                data=fields,
                timeout=90,
            )
        except requests.RequestException as exc:
            raise GnaniAPIError(502, "Could not reach Gnani Prisma. Check your connection and retry.") from exc

        payload = self._json_response(response, "Gnani Prisma request failed.")
        transcript = payload.get("transcript")
        if payload.get("success") is not True or not isinstance(transcript, str):
            raise GnaniAPIError(502, "Gnani did not return a successful transcript.")
        return payload

    def create_batch_job(
        self,
        audio_bytes: bytes,
        filename: str,
        language_code: str = "en-IN",
    ) -> dict[str, Any]:
        """Upload one audio file to the asynchronous Batch STT API."""
        if not audio_bytes:
            raise ValueError("Audio file is empty.")
        if len(audio_bytes) > 10 * 1024 * 1024:
            raise ValueError("Batch STT accepts files up to 10 MB each.")
        endpoint = f"{self.base_url}/stt/v3/batch/jobs"
        config = {
            "model": self.batch_stt_model,
            "language_code": language_code,
            "mode": "transcribe",
            "with_diarization": False,
            "is_multi_channel": False,
        }
        files = {
            "config": (None, json.dumps(config), "application/json"),
            "files": (Path(filename).name, audio_bytes, self._audio_mime(filename)),
        }
        try:
            response = requests.post(endpoint, headers=self.auth_headers(), files=files, timeout=120)
        except requests.RequestException as exc:
            raise GnaniAPIError(502, "Could not create a Gnani Batch STT job.") from exc
        payload = self._json_response(response, "Gnani Batch STT job creation failed.")
        if not payload.get("job_id"):
            raise GnaniAPIError(502, "Gnani did not return a Batch STT job ID.")
        return payload

    @staticmethod
    def _audio_mime(filename: str) -> str:
        return {
            ".wav": "audio/wav", ".mp3": "audio/mpeg", ".ogg": "audio/ogg",
            ".flac": "audio/flac", ".aac": "audio/aac", ".m4a": "audio/mp4",
        }.get(Path(filename).suffix.lower(), "application/octet-stream")

    def start_batch_job(self, job_id: str) -> dict[str, Any]:
        endpoint = f"{self.base_url}/stt/v3/batch/jobs/{job_id}/start"
        try:
            response = requests.post(endpoint, headers=self.auth_headers(), timeout=30)
        except requests.RequestException as exc:
            raise GnaniAPIError(502, "Could not start the Gnani Batch STT job.") from exc
        return self._json_response(response, "Gnani Batch STT start failed.")

    def get_batch_job(self, job_id: str) -> dict[str, Any]:
        endpoint = f"{self.base_url}/stt/v3/batch/jobs/{job_id}"
        try:
            response = requests.get(endpoint, headers=self.auth_headers(), timeout=30)
        except requests.RequestException as exc:
            raise GnaniAPIError(502, "Could not retrieve the Gnani Batch STT job.") from exc
        return self._json_response(response, "Gnani Batch STT status request failed.")

    def get_batch_files(self, job_id: str) -> dict[str, Any]:
        endpoint = f"{self.base_url}/stt/v3/batch/jobs/{job_id}/files"
        try:
            response = requests.get(
                endpoint, headers=self.auth_headers(),
                params={"limit": 100}, timeout=30,
            )
        except requests.RequestException as exc:
            raise GnaniAPIError(502, "Could not retrieve Gnani Batch STT files.") from exc
        return self._json_response(response, "Gnani Batch STT files request failed.")

    def download_batch_transcript(self, transcript_url: str) -> dict[str, Any]:
        """Download the short-lived pre-signed transcript URL without API credentials."""
        parsed = urlparse(transcript_url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("Gnani returned an invalid transcript download URL.")
        try:
            response = requests.get(transcript_url, timeout=60)
        except requests.RequestException as exc:
            raise GnaniAPIError(502, "Could not download the Gnani transcript.") from exc
        if not response.ok:
            raise GnaniAPIError(response.status_code, "Could not download the Gnani transcript.")
        try:
            payload = response.json()
        except ValueError as exc:
            raise GnaniAPIError(502, "Gnani transcript file was not valid JSON.") from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("full_transcript"), str):
            raise GnaniAPIError(502, "Gnani transcript file did not contain full_transcript.")
        return payload

    def synthesize_with_timbre(
        self,
        text: str,
        voice: str = "Nalini",
        language: str = "auto",
        speed: float = 1.0,
        container: str = "mp3",
    ) -> bytes:
        """Generate narration with Timbre v2.5 and return audio bytes."""
        if not text.strip():
            raise ValueError("Narration text cannot be empty.")
        if not self.tts_endpoint:
            raise RuntimeError("Configure GNANI_TTS_ENDPOINT in your local .env file.")
        if not 0.85 <= speed <= 1.15:
            raise ValueError("Timbre speed must be between 0.85 and 1.15.")
        if container not in {"mp3", "wav", "ogg"}:
            raise ValueError("Narration output must be mp3, wav, or ogg.")

        payload: dict[str, Any] = {
            "text": text,
            "model": "timbre-v2.5",
            "voice": voice,
            "language": language,
            "speed": speed,
            "audio_config": {
                "container": container,
                "num_channels": 1,
                "sample_rate": 24000 if container == "mp3" else 48000,
            },
        }
        if container != "mp3":
            payload["audio_config"]["encoding"] = "linear_pcm"
            payload["audio_config"]["sample_width"] = 2
        if container == "mp3":
            payload["audio_config"]["bitrate"] = "128k"

        try:
            response = requests.post(
                self.tts_endpoint, headers=self.auth_headers(), json=payload, timeout=180
            )
        except requests.RequestException as exc:
            raise GnaniAPIError(502, "Could not reach Gnani Timbre. Check your connection and retry.") from exc
        if not response.ok:
            self._raise_provider_error(response, "Gnani Timbre request failed.")
        if not response.content:
            raise GnaniAPIError(502, "Gnani Timbre returned an empty audio file.")
        return response.content

    def generate_with_llm(self, prompt: str) -> str:
        """Call a hosted OpenAI-compatible chat-completions API."""
        if not self.llm_endpoint or not self.llm_api_key:
            raise RuntimeError(
                "Configure both LLM_API_URL and LLM_API_KEY in your local .env file."
            )
        headers = {"Content-Type": "application/json"}
        if self.llm_api_key:
            headers["Authorization"] = f"Bearer {self.llm_api_key}"
        payload = {
            "model": self.llm_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are MOMENT AI. Follow the user's output schema exactly. "
                        "Use only source evidence. Never invent facts, attendees, "
                        "decisions, owners, deadlines, formulas, or citations. "
                        "Mark missing information as unknown."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "top_p": 0.9,
            "max_completion_tokens": 5000,
        }
        try:
            response = requests.post(
                self.llm_endpoint, headers=headers, json=payload, timeout=600
            )
        except requests.RequestException as exc:
            raise GnaniAPIError(
                502, "Could not reach the configured LLM provider."
            ) from exc
        result = self._json_response(response, "LLM provider request failed.")
        choices = result.get("choices")
        if not isinstance(choices, list) or not choices:
            raise GnaniAPIError(502, "LLM provider returned no completion choices.")
        message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
        generated = message.get("content") if isinstance(message, dict) else None
        if isinstance(generated, list):
            generated = "".join(
                part.get("text", "") for part in generated if isinstance(part, dict)
            )
        if not isinstance(generated, str) or not generated.strip():
            raise GnaniAPIError(502, "LLM provider returned an empty response.")
        return generated.strip()
