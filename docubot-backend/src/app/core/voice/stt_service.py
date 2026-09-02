"""
STT Service — Groq Whisper Large V3 audio transcription.
"""

from __future__ import annotations

import io
import logging
import os
from typing import Optional

from groq import AsyncGroq

from app.config import settings

_log = logging.getLogger(__name__)


class STTService:
    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or settings.groq_api_key or os.environ.get("GROQ_API_KEY", "")
        if self.api_key:
            self.client = AsyncGroq(api_key=self.api_key)
        else:
            self.client = None

    async def transcribe(
        self,
        audio_bytes: bytes,
        filename: str = "audio.webm",
        language: str = "en",
    ) -> str:
        """
        Transcribes the given audio bytes into text using Groq Whisper Large V3.
        """
        if not audio_bytes:
            return ""

        if not self.client:
            key = settings.groq_api_key or os.environ.get("GROQ_API_KEY", "")
            if key:
                self.client = AsyncGroq(api_key=key)
            else:
                raise ValueError("GROQ_API_KEY is not configured for Whisper STT.")

        try:
            file_tuple = (filename, io.BytesIO(audio_bytes))
            kwargs: dict = {
                "file": file_tuple,
                "model": "whisper-large-v3",
                "response_format": "json",
                "temperature": 0.0,
                "language": language or "en",
            }

            response = await self.client.audio.transcriptions.create(**kwargs)
            transcript = getattr(response, "text", "") or ""
            return transcript.strip()

        except Exception as exc:
            _log.exception("STT Transcription failed: %s", exc)
            raise RuntimeError(f"Voice transcription failed: {exc}") from exc
