"""
Playground API — nested under /workspaces/{workspace_id}/chatbots/{chatbot_id}/playground.

Allows workspace users (builders) to test their chatbots prior to deployment.
Does NOT check deployment status.
"""

from __future__ import annotations

import json
import logging
import uuid

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from app.api.dependencies import DbSession, WorkspaceMembership
from app.core.chat.engine import ChatEngine
from app.core.chat.session_service import ChatSessionService
from app.schemas.chat import (
    CreateSessionRequest,
    EndSessionRequest,
    MessageListOut,
    SessionEndedOut,
    SessionOut,
)

router = APIRouter(
    prefix="/workspaces/{workspace_id}/chatbots/{chatbot_id}/playground",
    tags=["playground"],
)
_log = logging.getLogger(__name__)


def _svc(session: DbSession) -> ChatSessionService:
    return ChatSessionService(session)


@router.post(
    "/session",
    response_model=SessionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new playground test session",
)
async def create_playground_session(
    workspace_id: uuid.UUID,
    chatbot_id: uuid.UUID,
    data: CreateSessionRequest,
    member: WorkspaceMembership,
    session: DbSession,
) -> SessionOut:
    return await _svc(session).create_playground_session(workspace_id, chatbot_id, data, member)


@router.get(
    "/session/{session_id}/messages",
    response_model=MessageListOut,
    summary="Retrieve conversation history for a playground session",
)
async def get_playground_messages(
    workspace_id: uuid.UUID,
    chatbot_id: uuid.UUID,
    session_id: uuid.UUID,
    member: WorkspaceMembership,
    session: DbSession,
    token: str = Query(..., description="Session token"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> MessageListOut:
    return await _svc(session).get_playground_messages(
        workspace_id, chatbot_id, session_id, token, limit, offset
    )


@router.post(
    "/session/{session_id}/end",
    response_model=SessionEndedOut,
    summary="End a playground chat session",
)
async def end_playground_session(
    workspace_id: uuid.UUID,
    chatbot_id: uuid.UUID,
    session_id: uuid.UUID,
    data: EndSessionRequest,
    member: WorkspaceMembership,
    session: DbSession,
    token: str = Query(..., description="Session token"),
) -> SessionEndedOut:
    return await _svc(session).end_playground_session(
        workspace_id, chatbot_id, session_id, token, data.summarize
    )


@router.websocket("/chat")
async def websocket_playground_chat(
    websocket: WebSocket,
    workspace_id: uuid.UUID,
    chatbot_id: uuid.UUID,
    session: DbSession,
    token: str = Query(..., description="Session token from POST /session"),
) -> None:
    """
    Playground WebSocket chat endpoint.
    """
    print(f"Playground WebSocket incoming! token={token}")
    await websocket.accept()
    engine = ChatEngine(session)

    try:
        await engine._validate_session(token)
    except Exception as exc:
        # Note: if session is expired, engine might raise ForbiddenError
        # Catch it and return the playground-specific payload if needed
        err_msg = str(exc)
        if "expired" in err_msg.lower():
            _log.warning(f"Playground WS rejected: session expired (token={token})")
            await websocket.send_json({"detail": "Playground session has expired."})
        else:
            _log.warning(f"Playground WS rejected: invalid session (token={token}, err={err_msg})")
            await websocket.send_json({"type": "error", "code": "INVALID_SESSION", "message": err_msg})
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
                    {"type": "error", "code": "UNKNOWN_EVENT", "message": f"Unknown event type: {event.get('type')}"}
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
                    {"type": "error", "code": "MESSAGE_TOO_LONG", "message": "Message exceeds 4000 character limit."}
                )
                continue

            try:
                response = await engine.handle_message(
                    session_token=token,
                    user_message=content,
                    is_playground=True
                )
                await websocket.send_json(response)
            except Exception as exc:
                err_msg = str(exc)
                if "Playground query limit reached" in err_msg:
                    await websocket.send_json({"detail": "Playground query limit reached."})
                else:
                    _log.exception("Error processing playground message: %s", exc)
                    await websocket.send_json(
                        {"type": "error", "code": "PROCESSING_ERROR", "message": err_msg}
                    )

    except WebSocketDisconnect:
        _log.debug("Playground WebSocket disconnected: workspace=%s chatbot=%s", workspace_id, chatbot_id)
    except Exception as exc:
        _log.error("Playground WebSocket error: %s", exc)
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
