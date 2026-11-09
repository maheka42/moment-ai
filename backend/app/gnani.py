"""Gnani API configuration and model adapters.

Endpoint paths and payload schemas are implemented only after checking the
specific official endpoint guides. The introduction page alone does not define
those request/response contracts.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class GnaniClient:
    base_url: str = "https://api.vachana.ai"
    api_key_id: str | None = None
    stt_endpoint: str | None = None
    tts_endpoint: str | None = None
    llm_endpoint: str | None = None

    @classmethod
    def from_env(cls) -> "GnaniClient":
        return cls(
            base_url=os.getenv("GNANI_BASE_URL", "https://api.vachana.ai").rstrip("/"),
            api_key_id=os.getenv("GNANI_API_KEY_ID"),
            stt_endpoint=os.getenv("GNANI_STT_ENDPOINT", "https://api.vachana.ai/stt/v3"),
            tts_endpoint=os.getenv("GNANI_TTS_ENDPOINT"),
            llm_endpoint=os.getenv("GNANI_LLM_ENDPOINT"),
        )

    def auth_headers(self) -> dict[str, str]:
        if not self.api_key_id:
            raise RuntimeError("Configure GNANI_API_KEY_ID in your local .env file.")
        return {"X-API-Key-ID": self.api_key_id}

    def transcribe_with_prisma(self, audio_path: str) -> dict:
        """Transcribe audio after the official STT REST guide is confirmed."""
        if not self.api_key_id:
            raise RuntimeError("Configure GNANI_API_KEY_ID in your local .env file.")
        if not self.stt_endpoint:
            raise RuntimeError("Configure GNANI_STT_ENDPOINT after checking the STT REST guide.")
        raise NotImplementedError(
            "The STT REST endpoint's multipart fields, model parameter, and response schema "
            "must be implemented from the official Prisma REST documentation."
        )

    def synthesize_with_timbre(self, text: str, output_path: str) -> str:
        """Synthesize speech after the official Timbre v2.5 REST guide is confirmed."""
        if not self.api_key_id:
            raise RuntimeError("Configure GNANI_API_KEY_ID in your local .env file.")
        if not self.tts_endpoint:
            raise RuntimeError("Configure GNANI_TTS_ENDPOINT after checking the TTS REST guide.")
        raise NotImplementedError(
            "The Timbre v2.5 request fields, voice selection, and audio response "
            "must be implemented from the official TTS REST documentation."
        )

    def generate_with_evon(self, prompt: str) -> str:
        """Evon open-weight inference adapter; no hosted endpoint is assumed."""
        raise NotImplementedError(
            "Select and configure a supported Evon inference runtime before enabling generation."
        )
