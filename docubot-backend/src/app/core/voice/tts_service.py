"""
TTS Service - Edge-TTS asynchronous streaming and sentence synthesis.
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import AsyncIterator
from typing import Optional

import edge_tts

from app.config import settings

_log = logging.getLogger(__name__)


def clean_text_for_speech(text: str) -> str:
    """
    Remove Markdown formatting, URLs, code blocks, and source citations
    to produce clean, natural spoken speech.
    """
    if not text:
        return ""

    # Remove Markdown code blocks
    cleaned = re.sub(r"```[\s\S]*?```", "", text)
    # Remove inline code
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
    # Remove markdown link formatting [text](url) -> text FIRST before url stripping
    cleaned = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", cleaned)
    # Remove standalone URLs
    cleaned = re.sub(r"https?://\S+|www\.\S+", "", cleaned)
    # Remove citation brackets e.g. [1], [Source: ...]
    cleaned = re.sub(r"\[(?:Source|Doc|Page|Ref)?\s*[^\]]*\]", "", cleaned, flags=re.IGNORECASE)
    # Remove bold/italic markers
    cleaned = re.sub(r"[*_~]{1,3}", "", cleaned)
    # Remove headers (#, ##, etc.)
    cleaned = re.sub(r"^#+\s*", "", cleaned, flags=re.MULTILINE)
    # Remove markdown table dividers and pipes
    cleaned = re.sub(r"\|[-:\s|]+\|", " ", cleaned)
    cleaned = re.sub(r"\|", " ", cleaned)
    # Remove bullet points and numbering
    cleaned = re.sub(r"^[\s*•\-–—]+\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^\d+\.\s*", "", cleaned, flags=re.MULTILINE)
    # Collapse multiple whitespace/newlines
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    # Remove spaces before punctuation
    cleaned = re.sub(r"\s+([.,!?;:])", r"\1", cleaned)

    # If no word characters exist, do not send empty symbols to TTS
    if not re.search(r"\w", cleaned):
        return ""

    return cleaned


class TTSService:
    def __init__(self, default_voice: Optional[str] = None) -> None:
        self.default_voice = default_voice or settings.default_tts_voice or "en-US-AriaNeural"

    async def synthesize_speech(
        self,
        text: str,
        voice: Optional[str] = None,
        rate: str = "+0%",
        pitch: str = "+0Hz",
    ) -> bytes:
        """
        Synthesizes a single sentence or text fragment into MP3 audio bytes using Edge-TTS.
        """
        speech_text = clean_text_for_speech(text)
        if not speech_text:
            return b""

        selected_voice = voice or self.default_voice
        communicate = edge_tts.Communicate(
            text=speech_text,
            voice=selected_voice,
            rate=rate,
            pitch=pitch,
        )

        audio_data = bytearray()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.extend(chunk["data"])

        return bytes(audio_data)

    async def stream_audio_chunks(
        self,
        text: str,
        voice: Optional[str] = None,
        rate: str = "+0%",
        pitch: str = "+0Hz",
        cancellation_event: Optional[asyncio.Event] = None,
    ) -> AsyncIterator[bytes]:
        """
        Synthesizes text to streaming MP3 audio chunks via Edge-TTS.
        Periodically checks `cancellation_event` to support instant barge-in.
        """
        speech_text = clean_text_for_speech(text)
        if not speech_text:
            return

        selected_voice = voice or self.default_voice

        try:
            communicate = edge_tts.Communicate(
                text=speech_text,
                voice=selected_voice,
                rate=rate,
                pitch=pitch,
            )

            async for chunk in communicate.stream():
                if cancellation_event and cancellation_event.is_set():
                    _log.debug("TTS stream interrupted by client cancellation event.")
                    break

                if chunk["type"] == "audio":
                    yield chunk["data"]

        except asyncio.CancelledError:
            _log.debug("TTS task was cancelled.")
            raise
        except Exception as exc:
            _log.exception("Edge-TTS streaming failed: %s", exc)
            raise RuntimeError(f"Text-to-speech synthesis failed: {exc}") from exc
