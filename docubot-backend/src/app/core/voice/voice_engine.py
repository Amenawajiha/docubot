"""
VoiceEngine - WebSocket orchestrator for voice chat sessions.

Reuses proven ragvoicebot low-latency architecture:
  1. Receives raw binary Opus/WebM audio frames over WebSocket
  2. Aligns WebM EBML header (\x1a\x45\xdf\xa3) to ensure clean decoding
  3. Rejects empty payloads & common Whisper silence hallucinations
  4. Passes transcribed utterance to DocuBot ChatEngine for RAG retrieval & persistence
  5. Streams sentences to Edge-TTS pipeline for near-instant audio playback
  6. Supports instant barge-in/interruption and text fallback
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import re
from typing import Any, Optional

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.chat.engine import ChatEngine
from app.core.voice.stt_service import STTService
from app.core.voice.tts_service import TTSService

_log = logging.getLogger(__name__)

SENTENCE_SPLIT_REGEX = re.compile(r"([.?!.\n])\s*")

HALLUCINATION_PATTERNS = [
    re.compile(r"thank(s)?\s*(you)?.*for\s+watching", re.I),
    re.compile(r"subtitles\s+by", re.I),
    re.compile(r"amara\.org", re.I),
    re.compile(r"like\s+and\s+subscribe", re.I),
    re.compile(r"subscribe\s+to\s+my\s+channel", re.I),
    re.compile(r"for\s+more\s+videos", re.I),
    re.compile(r"^(\b\w+\b)(?:[\s,.]+\1\b){2,}\.?$", re.I),  # "hello, hello, hello" or "bye bye bye"
]

HALLUCINATION_EXACT = {
    "thank you", "thank you.", "thank you thank you", "thank you. thank you.",
    "thanks", "thanks.", "thanks for watching", "subtitles by", "amara.org", "you",
    "bye", "goodbye", "hello", "hello.", "hello hello", "so", "so.", "yeah", "yes.",
    "duh", "blah", "blah blah", "blah blah blah"
}
HALLUCINATION_SET = HALLUCINATION_EXACT


def is_silence_hallucination(text: str) -> bool:
    clean = text.strip().strip(".!?, \n\t").lower()
    if not clean or len(clean) < 3:
        return True
    if clean in HALLUCINATION_EXACT:
        return True
    for pat in HALLUCINATION_PATTERNS:
        if pat.search(text):
            return True
    return False


class VoiceEngine:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.chat_engine = ChatEngine(db)
        self.stt_service = STTService()
        self.tts_service = TTSService()

    async def handle_voice_session(
        self,
        websocket: WebSocket,
        session_token: str,
        is_playground: bool = False,
    ) -> None:
        """
        Manages the full lifecycle of a voice WebSocket connection.
        """
        # Validate DocuBot session token
        try:
            await self.chat_engine._validate_session(session_token)
        except Exception as exc:
            err_msg = str(exc)
            _log.warning("Voice WS rejected: %s (token=%s)", err_msg, session_token)
            if "expired" in err_msg.lower():
                await websocket.send_json({"detail": "Session has expired."})
            else:
                await websocket.send_json({"type": "error", "code": "INVALID_SESSION", "message": err_msg})
            await websocket.close(code=1008)
            return

        audio_buffer = bytearray()
        is_processing = False
        active_task: Optional[asyncio.Task] = None

        await websocket.send_json({"type": "status", "status": "ready"})

        try:
            while True:
                message = await websocket.receive()

                if message.get("type") == "websocket.disconnect":
                    _log.info("Voice WebSocket disconnected cleanly.")
                    break

                # ── Handle Raw Binary Audio Frames ──
                if "bytes" in message:
                    chunk = message["bytes"]
                    if chunk:
                        audio_buffer.extend(chunk)
                    continue

                # ── Handle JSON Text Control Frames ──
                if "text" in message:
                    try:
                        event: dict[str, Any] = json.loads(message["text"])
                    except Exception as parse_err:
                        _log.warning("Failed to parse JSON frame: %s", parse_err)
                        continue

                    event_type = event.get("type")

                    if event_type in ("start", "start_turn"):
                        audio_buffer.clear()
                        is_processing = False
                        if active_task and not active_task.done():
                            active_task.cancel()
                        if event_type == "start":
                            await websocket.send_json({"type": "status", "status": "ready"})

                    elif event_type == "interrupt":
                        _log.info("Interrupt event received (Barge-in).")
                        is_processing = False
                        audio_buffer.clear()
                        if active_task and not active_task.done():
                            active_task.cancel()
                        await websocket.send_json({"type": "status", "status": "ready"})

                    elif event_type in ("stop", "commit"):
                        if is_processing:
                            continue

                        is_processing = True
                        await websocket.send_json({"type": "status", "status": "processing"})

                        audio_bytes = bytes(audio_buffer)
                        audio_buffer.clear()

                        # Strip corrupted prefix bytes before the WebM EBML header
                        ebml_idx = audio_bytes.find(b"\x1a\x45\xdf\xa3")
                        if ebml_idx > 0:
                            _log.debug("Stripped %d prefix bytes for clean WebM EBML alignment", ebml_idx)
                            audio_bytes = audio_bytes[ebml_idx:]

                        # Filter out empty noise packets (less than 500 bytes is just empty header)
                        if len(audio_bytes) < 500:
                            _log.info("Audio payload too small (%d bytes), ignoring silence.", len(audio_bytes))
                            await websocket.send_json({"type": "status", "status": "ready"})
                            is_processing = False
                            continue

                        # Execute STT transcription
                        try:
                            _log.info("Transcribing %d bytes of audio...", len(audio_bytes))
                            user_transcript = await self.stt_service.transcribe(
                                audio_bytes=audio_bytes,
                                filename="audio.webm",
                            )
                            _log.info("Whisper STT result: '%s'", user_transcript)
                        except Exception as stt_err:
                            _log.exception("STT Transcription failed: %s", stt_err)
                            await websocket.send_json({
                                "type": "error",
                                "code": "STT_ERROR",
                                "message": f"Transcription error: {stt_err}"
                            })
                            await websocket.send_json({"type": "status", "status": "ready"})
                            is_processing = False
                            continue

                        if not is_processing:
                            continue

                        # Filter out ambient silence / Whisper hallucinations
                        if is_silence_hallucination(user_transcript):
                            _log.info("Ignored ambient noise / STT hallucination: '%s'", user_transcript)
                            await websocket.send_json({"type": "status", "status": "ready"})
                            is_processing = False
                            continue

                        # Emit recognized user transcript to client
                        await websocket.send_json({
                            "type": "transcript",
                            "sender": "user",
                            "text": user_transcript,
                            "isFinal": True,
                        })

                        # Execute RAG query and sentence-based TTS pipelining
                        await self._process_text_query(
                            websocket=websocket,
                            session_token=session_token,
                            query_text=user_transcript,
                            is_playground=is_playground,
                        )
                        is_processing = False

                    elif event_type in ("text", "text_input"):
                        query_text = (event.get("text") or "").strip()
                        if not query_text:
                            continue

                        is_processing = True
                        audio_buffer.clear()
                        if active_task and not active_task.done():
                            active_task.cancel()

                        await self._process_text_query(
                            websocket=websocket,
                            session_token=session_token,
                            query_text=query_text,
                            is_playground=is_playground,
                        )
                        is_processing = False

        except WebSocketDisconnect:
            _log.info("Voice WebSocket client disconnected.")
            if active_task and not active_task.done():
                active_task.cancel()
        except Exception as ws_err:
            _log.error("Voice WebSocket runtime error: %s", ws_err)
            if active_task and not active_task.done():
                active_task.cancel()
            try:
                await websocket.close(code=1011)
            except Exception:
                pass

    async def _process_text_query(
        self,
        websocket: WebSocket,
        session_token: str,
        query_text: str,
        is_playground: bool,
    ) -> None:
        """
        Executes ChatEngine RAG retrieval, splits into sentences,
        and pipelines TTS synthesis chunks back to the client.
        """
        await websocket.send_json({"type": "status", "status": "playing"})

        try:
            rag_response = await self.chat_engine.handle_message(
                session_token=session_token,
                user_message=query_text,
                is_playground=is_playground,
            )
        except Exception as exc:
            err_msg = str(exc)
            if "Playground query limit reached" in err_msg:
                await websocket.send_json({"detail": "Playground query limit reached."})
            else:
                _log.exception("RAG processing error: %s", exc)
                await websocket.send_json({
                    "type": "error",
                    "code": "PROCESSING_ERROR",
                    "message": err_msg,
                })
            await websocket.send_json({"type": "status", "status": "ready"})
            return

        if rag_response.get("type") == "error":
            await websocket.send_json(rag_response)
            await websocket.send_json({"type": "status", "status": "ready"})
            return

        assistant_text = rag_response.get("content") or rag_response.get("clarification_question") or ""
        sources = rag_response.get("sources") or []

        if not assistant_text:
            await websocket.send_json({
                "type": "transcript",
                "sender": "assistant",
                "text": "",
                "isFinal": True,
                "sources": sources,
            })
            await websocket.send_json({"type": "status", "status": "ready"})
            return

        # Sentence-level parsing and streaming synthesis
        sentences: list[str] = []
        last_idx = 0
        for match in SENTENCE_SPLIT_REGEX.finditer(assistant_text):
            sentence = assistant_text[last_idx:match.end()].strip()
            last_idx = match.end()
            if len(sentence) > 1:
                sentences.append(sentence)

        remainder = assistant_text[last_idx:].strip()
        if remainder:
            sentences.append(remainder)

        if not sentences:
            sentences = [assistant_text]

        for sentence in sentences:
            # Emit partial transcript
            await websocket.send_json({
                "type": "transcript",
                "sender": "assistant",
                "text": sentence + " ",
                "isFinal": False,
                "sources": sources,
            })

            # Synthesize speech for this sentence
            try:
                audio_mp3 = await self.tts_service.synthesize_speech(sentence)
                if audio_mp3:
                    audio_b64 = base64.b64encode(audio_mp3).decode("utf-8")
                    await websocket.send_json({
                        "type": "audio",
                        "data": audio_b64,
                        "text": sentence,
                    })
            except Exception as synth_err:
                _log.error("Failed synthesizing sentence chunk: %s", synth_err)

        # Emit completion transcript & status ready
        await websocket.send_json({
            "type": "transcript",
            "sender": "assistant",
            "text": assistant_text,
            "isFinal": True,
            "sources": sources,
        })
        await websocket.send_json({"type": "status", "status": "ready"})
