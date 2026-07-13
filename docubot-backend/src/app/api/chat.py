"""
End-user chat endpoints.

Public-facing — authenticated by session token (NOT workspace JWT).

Routes:
  POST  /chatbot/{workspace_slug}/{chatbot_id}/session
  GET   /chatbot/{workspace_slug}/{chatbot_id}/session/{session_id}/messages
  POST  /chatbot/{workspace_slug}/{chatbot_id}/session/{session_id}/end
  WS    /chatbot/{workspace_slug}/{chatbot_id}/chat
"""

from __future__ import annotations

import json
import logging
import uuid

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from app.api.dependencies import DbSession
from app.core.chat.engine import ChatEngine
from app.core.chat.session_service import ChatSessionService
from app.schemas.chat import (
    CreateSessionRequest,
    EndSessionRequest,
    MessageListOut,
    SessionEndedOut,
    SessionOut,
)

router = APIRouter(prefix="/chatbot", tags=["chat"])
_log = logging.getLogger(__name__)


def _svc(session: DbSession) -> ChatSessionService:
    return ChatSessionService(session)


# ── Session management ────────────────────────────────────────────────────────

@router.post(
    "/{workspace_slug}/{chatbot_id}/session",
    response_model=SessionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new end-user chat session",
    description=(
        "Returns a session_token valid for 4 hours. "
        "Pass this token in the WebSocket query string: ?token=<session_token>."
    ),
)
async def create_session(
    workspace_slug: str,
    chatbot_id: uuid.UUID,
    data: CreateSessionRequest,
    session: DbSession,
) -> SessionOut:
    return await _svc(session).create_session(workspace_slug, chatbot_id, data)


@router.get(
    "/{workspace_slug}/{chatbot_id}/session/{session_id}/messages",
    response_model=MessageListOut,
    summary="Retrieve conversation history for a session",
)
async def get_messages(
    workspace_slug: str,
    chatbot_id: uuid.UUID,
    session_id: uuid.UUID,
    session: DbSession,
    token: str = Query(..., description="Session token"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> MessageListOut:
    return await _svc(session).get_messages(
        workspace_slug, chatbot_id, session_id, token, limit, offset
    )


@router.post(
    "/{workspace_slug}/{chatbot_id}/session/{session_id}/end",
    response_model=SessionEndedOut,
    summary="End a chat session",
)
async def end_session(
    workspace_slug: str,
    chatbot_id: uuid.UUID,
    session_id: uuid.UUID,
    data: EndSessionRequest,
    session: DbSession,
    token: str = Query(..., description="Session token"),
) -> SessionEndedOut:
    return await _svc(session).end_session(
        workspace_slug, chatbot_id, session_id, token, data.summarize
    )


# ── WebSocket chat ────────────────────────────────────────────────────────────

@router.websocket("/{workspace_slug}/{chatbot_id}/chat")
async def websocket_chat(
    websocket: WebSocket,
    workspace_slug: str,
    chatbot_id: uuid.UUID,
    session: DbSession,
    token: str = Query(..., description="Session token from POST /session"),
) -> None:
    """
    Bidirectional WebSocket chat endpoint.

    Connection URL:
        ws://localhost:8000/api/v1/chatbot/{workspace_slug}/{chatbot_id}/chat?token=<token>

    Client sends:
        { "type": "message", "content": "What is the refund policy?" }

    Server sends (complete response):
        {
            "type": "response",
            "content": "The refund policy is...",
            "confidence": 0.92,
            "sources": [...],
            "clarification_question": null,
            "tokens": { "input": 45, "output": 120 },
            "execution_time_ms": 1340
        }

    Server sends (error):
        { "type": "error", "code": "QUOTA_EXCEEDED", "message": "..." }
    """
    print(f"WebSocket incoming! token={token}")
    await websocket.accept()
    engine = ChatEngine(session)

    # Validate the session token before allowing any messages
    try:
        await engine._validate_session(token)
    except Exception as exc:
        await websocket.send_json(
            {"type": "error", "code": "INVALID_SESSION", "message": str(exc)}
        )
        await websocket.close(code=1008)
        return

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json(
                    {"type": "error", "code": "INVALID_JSON", "message": "Invalid JSON."}
                )
                continue

            if event.get("type") != "message":
                await websocket.send_json(
                    {
                        "type": "error",
                        "code": "UNKNOWN_EVENT",
                        "message": f"Unknown event type: {event.get('type')}",
                    }
                )
                continue

            content = (event.get("content") or "").strip()
            if not content:
                await websocket.send_json(
                    {"type": "error", "code": "EMPTY_MESSAGE", "message": "Message cannot be empty."}
                )
                continue

            if len(content) > 4000:
                await websocket.send_json(
                    {
                        "type": "error",
                        "code": "MESSAGE_TOO_LONG",
                        "message": "Message exceeds 4000 character limit.",
                    }
                )
                continue

            # Process message through the engine
            try:
                response = await engine.handle_message(
                    session_token=token,
                    user_message=content,
                )
                await websocket.send_json(response)
            except Exception as exc:
                _log.exception("Error processing chat message: %s", exc)
                await websocket.send_json(
                    {
                        "type": "error",
                        "code": "PROCESSING_ERROR",
                        "message": str(exc),
                    }
                )

    except WebSocketDisconnect:
        _log.debug("WebSocket disconnected: workspace=%s chatbot=%s",
                   workspace_slug, chatbot_id)
    except Exception as exc:
        _log.error("WebSocket error: %s", exc)
        try:
            await websocket.close(code=1011)
        except Exception:
            pass