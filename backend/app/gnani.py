"""Gnani API adapters based on the official REST documentation."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
    tts_endpoint: str | None = None
    llm_endpoint: str | None = None

    @classmethod
    def from_env(cls) -> "GnaniClient":
        base_url = os.getenv("GNANI_BASE_URL", "https://api.vachana.ai").rstrip("/")
        return cls(
            base_url=base_url,
            api_key_id=os.getenv("GNANI_API_KEY_ID"),
            stt_endpoint=os.getenv("GNANI_STT_ENDPOINT", f"{base_url}/stt/v3"),
            tts_endpoint=os.getenv("GNANI_TTS_ENDPOINT"),
            llm_endpoint=os.getenv("GNANI_LLM_ENDPOINT"),
        )

    def auth_headers(self) -> dict[str, str]:
        if not self.api_key_id:
            raise RuntimeError("Configure GNANI_API_KEY_ID in your local .env file.")
        return {"X-API-Key-ID": self.api_key_id}

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
        """Call Prisma v3.0 REST. The endpoint accepts audio up to 30 seconds."""
        if not audio_bytes:
            raise ValueError("Audio file is empty.")
        if not self.api_key_id:
            raise RuntimeError("Configure GNANI_API_KEY_ID in your local .env file.")
        if not self.stt_endpoint:
            raise RuntimeError("Configure GNANI_STT_ENDPOINT in your local .env file.")
        if output_format not in {"verbatim", "transcribe", "codemix", "transliterate"}:
            raise ValueError("Unsupported Prisma v3.0 output format.")
        if not language_code and output_format != "transliterate":
            raise ValueError("language_code is required unless format is transliterate.")

        fields: dict[str, str] = {
            "model": "prisma-v3.0",
            "format": output_format,
        }
        if language_code:
            fields["language_code"] = language_code
        if topic:
            fields["topic"] = topic
        if keyterms:
            fields["keyterms"] = json.dumps(keyterms, ensure_ascii=False)
        if previous_text:
            fields["previous_text"] = previous_text
        if speaker_names:
            fields["speaker_names"] = json.dumps(speaker_names, ensure_ascii=False)

        headers = self.auth_headers()
        if request_id:
            headers["X-API-Request-ID"] = request_id

        suffix = Path(filename).suffix.lower()
        mime_types = {
            ".wav": "audio/wav",
            ".mp3": "audio/mpeg",
            ".ogg": "audio/ogg",
            ".flac": "audio/flac",
            ".aac": "audio/aac",
            ".m4a": "audio/mp4",
        }
        mime_type = mime_types.get(suffix, "application/octet-stream")

        try:
            response = requests.post(
                self.stt_endpoint,
                headers=headers,
                files={"audio_file": (Path(filename).name, audio_bytes, mime_type)},
                data=fields,
                timeout=60,
            )
        except requests.RequestException as exc:
            raise GnaniAPIError(502, "Could not reach Gnani Prisma. Check your connection and retry.") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise GnaniAPIError(response.status_code, "Gnani returned an unreadable response.") from exc

        if not response.ok:
            error = payload.get("error", {}) if isinstance(payload, dict) else {}
            detail = payload.get("detail", {}) if isinstance(payload, dict) else {}
            message = (
                error.get("message")
                if isinstance(error, dict)
                else None
            ) or (
                detail.get("message")
                if isinstance(detail, dict)
                else None
            ) or "Gnani Prisma request failed."
            error_type = error.get("type") if isinstance(error, dict) else None
            error_code = detail.get("error_code") if isinstance(detail, dict) else None
            raise GnaniAPIError(response.status_code, message, error_type or error_code)

        transcript = payload.get("transcript") if isinstance(payload, dict) else None
        if not isinstance(transcript, str):
            raise GnaniAPIError(502, "Gnani response did not contain a valid transcript.")
        if payload.get("success") is not True:
            raise GnaniAPIError(502, "Gnani did not confirm transcription success.")

        return payload

    def synthesize_with_timbre(self, text: str, output_path: str) -> str:
        """Timbre v2.5 adapter; implement after reviewing its REST contract."""
        if not self.api_key_id:
            raise RuntimeError("Configure GNANI_API_KEY_ID in your local .env file.")
        raise NotImplementedError("Timbre v2.5 REST request and response contract is not implemented yet.")

    def generate_with_evon(self, prompt: str) -> str:
        """Evon open-weight inference adapter; no hosted endpoint is assumed."""
        raise NotImplementedError(
            "Select and configure a supported Evon inference runtime before enabling generation."
        )
