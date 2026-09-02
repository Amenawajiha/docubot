"""
Unit tests for DocuBot Voice Services (STT, TTS, VoiceEngine, text sanitization).
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.voice.tts_service import TTSService, clean_text_for_speech
from app.core.voice.stt_service import STTService
from app.core.voice.voice_engine import VoiceEngine, HALLUCINATION_SET


def test_clean_text_for_speech():
    # Test code block removal
    text1 = "Here is the answer: ```python\nprint('hello')\n``` That is all."
    assert "print('hello')" not in clean_text_for_speech(text1)
    assert "Here is the answer: That is all." in clean_text_for_speech(text1)

    # Test Markdown link formatting
    text2 = "Please visit [our website](https://example.com/docs) for more info."
    cleaned2 = clean_text_for_speech(text2)
    assert cleaned2 == "Please visit our website for more info."

    # Test citations removal
    text3 = "DocuBot is an AI assistant [1] [Source: doc.pdf]."
    cleaned3 = clean_text_for_speech(text3)
    assert cleaned3 == "DocuBot is an AI assistant."

    # Test bold/italic removal
    text4 = "This is **very** _important_ *text*."
    cleaned4 = clean_text_for_speech(text4)
    assert cleaned4 == "This is very important text."


def test_stt_hallucination_filtering():
    assert "thank you." in HALLUCINATION_SET
    assert "thanks for watching" in HALLUCINATION_SET
    assert "amara.org" in HALLUCINATION_SET
    assert "hello" in HALLUCINATION_SET


def test_stt_service_initialization():
    stt = STTService(api_key="gsk_test_mock_key")
    assert stt.api_key == "gsk_test_mock_key"
    assert stt.client is not None


@pytest.mark.asyncio
async def test_stt_transcribe_empty():
    stt = STTService(api_key="gsk_test_mock_key")
    result = await stt.transcribe(b"")
    assert result == ""


@pytest.mark.asyncio
async def test_stt_transcribe_mock():
    stt = STTService(api_key="gsk_test_mock_key")
    mock_resp = MagicMock()
    mock_resp.text = "Hello, this is a test question."

    with patch.object(stt.client.audio.transcriptions, "create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_resp
        transcript = await stt.transcribe(b"fake_audio_bytes", filename="audio.webm")
        assert transcript == "Hello, this is a test question."
        mock_create.assert_called_once()


def test_tts_service_initialization():
    tts = TTSService(default_voice="en-US-JennyNeural")
    assert tts.default_voice == "en-US-JennyNeural"


@pytest.mark.asyncio
async def test_tts_stream_chunks_cancellation():
    tts = TTSService()
    cancel_event = asyncio.Event()
    cancel_event.set()  # Cancel immediately

    chunks = []
    async for chunk in tts.stream_audio_chunks("This should not be synthesized", cancellation_event=cancel_event):
        chunks.append(chunk)

    assert len(chunks) == 0


@pytest.mark.asyncio
async def test_voice_engine_initialization():
    mock_db = AsyncMock()
    engine = VoiceEngine(mock_db)

    # Verify components initialized
    assert engine.chat_engine is not None
    assert engine.stt_service is not None
    assert engine.tts_service is not None
