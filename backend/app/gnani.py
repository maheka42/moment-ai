"""Gnani model adapter placeholders.

Implement request/response handling only after checking the current official API
contracts. Do not guess endpoints, authentication headers, or payload schemas.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class GnaniClient:
    api_key: str | None = None
    stt_endpoint: str | None = None
    tts_endpoint: str | None = None
    llm_endpoint: str | None = None

    @classmethod
    def from_env(cls) -> "GnaniClient":
        return cls(
            api_key=os.getenv("GNANI_API_KEY"),
            stt_endpoint=os.getenv("GNANI_STT_ENDPOINT"),
            tts_endpoint=os.getenv("GNANI_TTS_ENDPOINT"),
            llm_endpoint=os.getenv("GNANI_LLM_ENDPOINT"),
        )

    def transcribe_with_prisma(self, audio_path: str) -> dict:
        """Transcribe audio with Prisma after its API contract is configured."""
        if not self.api_key or not self.stt_endpoint:
            raise RuntimeError("Configure GNANI_API_KEY and GNANI_STT_ENDPOINT.")
        raise NotImplementedError(
            "Add the verified Prisma API request and response mapping from Gnani docs."
        )

    def synthesize_with_timbre(self, text: str, output_path: str) -> str:
        """Create speech audio with Timbre after its API contract is configured."""
        if not self.api_key or not self.tts_endpoint:
            raise RuntimeError("Configure GNANI_API_KEY and GNANI_TTS_ENDPOINT.")
        raise NotImplementedError(
            "Add the verified Timbre API request and response mapping from Gnani docs."
        )

    def generate_with_evon(self, prompt: str) -> str:
        """Generate structured content with a configured Evon runtime.

        Evon is distributed as an open-weight model. This method intentionally
        does not assume an undocumented hosted inference endpoint.
        """
        raise NotImplementedError(
            "Configure a supported Evon inference runtime and implement its adapter."
        )
