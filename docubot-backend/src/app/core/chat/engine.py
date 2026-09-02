"""
ChatEngine â€” WebSocket orchestrator for end-user chat.

Responsibilities per message:
  1. Validate session token
  2. Check workspace token quota (Redis-cached)
  3. Fetch conversation history from DB
  4. Load chatbot config (DB â†’ decrypt API key)
  5. POST to chatbot-rag /api/chat (stateless call)
  6. Store user message + assistant message in DB
  7. Log token usage
  8. Return response JSON to WebSocket client

chatbot-rag contract (what we POST to it):
  {
    "workspace_id":   "...",
    "chatbot_id":     "...",
    "session_id":     "...",
    "message":        "user text",
    "history":        [{"role": "user", "content": "..."}, ...],
    "chatbot_config": { llm_provider, llm_model, api_key, system_prompt, ... }
  }

chatbot-rag response:
  {
    "response":               "assistant text",
    "confidence":             0.92,
    "sources":                [...],
    "clarification_question": null | "Did you mean X or Y?",
    "tokens":                 { "input": 45, "output": 120 },
    "execution_time_ms":      1340
  }
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import timezone
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.billing.cost_calculator import calculate_cost
from app.core.chat.session_service import ChatSessionService
from app.data.repositories.chat_repo import (
    ChatMessageRepository,
    ChatSessionRepository,
    UsageLogRepository,
)
from app.data.repositories.chatbot_repo import ChatbotRepository
from app.data.repositories.workspace_repo import WorkspaceRepository
from app.infrastructure.cache.redis_client import get_redis
from app.utils.exceptions import BadRequestError, ForbiddenError
from app.utils.security import decrypt_api_key

_log = logging.getLogger(__name__)

# Global httpx client for chatbot-rag communication
_rag_client = httpx.AsyncClient(timeout=120)

# Redis key for quota cache â€” 5-minute TTL so we don't hit DB on every message
_QUOTA_CACHE_TTL = 300


class ChatEngine:
    def __init__(self, db: AsyncSession) -> None:
        self.db       = db
        self.ses_repo = ChatSessionRepository(db)
        self.msg_repo = ChatMessageRepository(db)
        self.bot_repo = ChatbotRepository(db)
        self.ws_repo  = WorkspaceRepository(db)
        self.use_repo = UsageLogRepository(db)

    async def handle_message(
        self,
        session_token: str,
        user_message: str,
        is_playground: bool = False,
    ) -> dict[str, Any]:
        """
        Full message processing pipeline.
        Returns the dict to send back over the WebSocket.
        """
        # 1. Validate session
        session = await self._validate_session(session_token)

        # 2. Quota check
        if not is_playground:
            await self._check_quota(session.workspace_id)
        elif session.message_count >= 100:
            raise BadRequestError("Playground query limit reached. Please deploy your chatbot to continue.")

        # 3. Load chatbot + config
        chatbot = await self.bot_repo.get_by_id_in_workspace(
            session.chatbot_id, session.workspace_id
        )
        if not chatbot:
            return _err("CHATBOT_NOT_FOUND", "Chatbot not found.")

        workspace = await self.ws_repo.get_by_id(session.workspace_id)
        company_name = workspace.name if workspace else "Company"

        config = _build_config_payload(chatbot, company_name)

        # 4. Fetch recent conversation history (last context_depth messages)
        history_msgs = await self.msg_repo.get_recent_for_session(
            session.id, limit=chatbot.context_depth
        )
        history = [
            {"role": m.role, "content": m.content}
            for m in history_msgs
        ]

        # 5. Store user message in DB immediately
        user_msg = await self.msg_repo.create(
            workspace_id=session.workspace_id,
            chatbot_id=session.chatbot_id,
            session_id=session.id,
            end_user_id=session.end_user_id,
            role="user",
            content=user_message,
        )

        # 6. Call chatbot-rag /api/chat
        rag_response = await self._call_rag(
            workspace_id=session.workspace_id,
            chatbot_id=session.chatbot_id,
            session_id=session.id,
            message=user_message,
            history=history,
            config=config,
        )

        if "error" in rag_response:
            return _err("RAG_ERROR", rag_response["error"])

        tokens_in  = rag_response.get("tokens", {}).get("input", 0)
        tokens_out = rag_response.get("tokens", {}).get("output", 0)

        # 7. Store assistant message
        await self.msg_repo.create(
            workspace_id=session.workspace_id,
            chatbot_id=session.chatbot_id,
            session_id=session.id,
            end_user_id=session.end_user_id,
            role="assistant",
            content=rag_response.get("response", ""),
            tokens_input=tokens_in,
            tokens_output=tokens_out,
            confidence_score=str(rag_response.get("confidence", 0)),
            sources=rag_response.get("sources"),
            metadata_={
                "clarification_question": rag_response.get("clarification_question"),
                "execution_time_ms":      rag_response.get("execution_time_ms"),
            },
        )

        # 7b. Process conversation summarization and database history purging
        if rag_response.get("was_summarized") and rag_response.get("summary_text"):
            await self.msg_repo.purge_old_messages_for_session(session.id, keep_recent=10)
            await self.msg_repo.insert_summary_message(
                workspace_id=session.workspace_id,
                chatbot_id=session.chatbot_id,
                session_id=session.id,
                end_user_id=session.end_user_id,
                summary_text=rag_response["summary_text"],
            )

        # 8. Update session stats
        await self.ses_repo.increment_message_count(
            session, tokens=tokens_in + tokens_out
        )

        # Calculate cost dynamically via placeholder
        cost_usd = calculate_cost(
            provider=chatbot.llm_provider,
            model=chatbot.llm_model,
            tokens_input=tokens_in,
            tokens_output=tokens_out
        )

        from app.core.analytics.service import AnalyticsService
        await AnalyticsService(self.db).record_chat_event(
            workspace_id=session.workspace_id,
            chatbot_id=session.chatbot_id,
            session_id=session.id,
            event_type="message_sent",
            confidence=rag_response.get("confidence", 0.0),
            tokens_used=tokens_in + tokens_out,
            response_time_ms=rag_response.get("execution_time_ms"),
            content=user_message,
            cost_usd=cost_usd,
            end_user_id=session.end_user_id,
        )

        # 9. Log token usage
        if not is_playground:
            await self.use_repo.log_usage(
                workspace_id=session.workspace_id,
                chatbot_id=session.chatbot_id,
                session_id=session.id,
                tokens_input=tokens_in,
                tokens_output=tokens_out,
                cost_usd=cost_usd,
            )

            # 10. Invalidate quota cache (usage just increased)
            redis = await get_redis()
            await redis.delete(f"quota:{session.workspace_id}")

        return {
            "type":                    "response",
            "content":                 rag_response.get("response", ""),
            "confidence":              rag_response.get("confidence"),
            "sources":                 rag_response.get("sources", []),
            "clarification_question":  rag_response.get("clarification_question"),
            "tokens":                  {"input": tokens_in, "output": tokens_out},
            "execution_time_ms":       rag_response.get("execution_time_ms"),
        }

    # â”€â”€ Private helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    async def _validate_session(self, token: str):
        return await ChatSessionService(self.db).validate_session_token(token)

    async def _check_quota(self, workspace_id: uuid.UUID) -> None:
        redis = await get_redis()
        cache_key = f"quota:{workspace_id}"
        cached = await redis.get(cache_key)

        if cached:
            data = json.loads(cached)
        else:
            ws = await self.ws_repo.get_by_id_active(workspace_id)
            if not ws:
                raise BadRequestError("Workspace not found.")
            repo = UsageLogRepository(self.db)
            data = await repo.check_monthly_quota(
                workspace_id, ws.monthly_message_limit * 1000
            )
            await redis.setex(cache_key, _QUOTA_CACHE_TTL, json.dumps(data))

        if not data["allowed"]:
            raise BadRequestError(
                data.get("reason") or "Monthly quota exceeded."
            )

    async def _call_rag(
        self,
        workspace_id: uuid.UUID,
        chatbot_id: uuid.UUID,
        session_id: uuid.UUID,
        message: str,
        history: list[dict],
        config: dict,
    ) -> dict[str, Any]:
        """POST to chatbot-rag /api/chat. Returns parsed JSON response."""
        payload = {
            "workspace_id": str(workspace_id),
            "chatbot_id":   str(chatbot_id),
            "session_id":   str(session_id),
            "message":      message,
            "history":      history,
            "chatbot_config": config,
        }
        headers = {
            "X-Internal-API-Key": settings.internal_api_key,
            "Content-Type":       "application/json",
        }
        try:
            resp = await _rag_client.post(
                f"{settings.chatbot_rag_url}/api/chat",
                json=payload,
                headers=headers,
            )
            if resp.status_code != 200:
                _log.error(
                    "chatbot-rag /api/chat returned %s: %s",
                    resp.status_code, resp.text
                )
                return {"error": f"Chat engine error ({resp.status_code})."}
            return resp.json()
        except httpx.TimeoutException:
            return {"error": "Chat engine timed out. Please try again."}
        except Exception as exc:
            _log.exception("chatbot-rag call failed: %s", exc)
            return {"error": "Chat engine unavailable."}


def _build_config_payload(chatbot, company_name: str) -> dict:
    """Build the config dict we send to chatbot-rag per request."""
    raw_key: str | None = None
    if chatbot.custom_api_key_encrypted:
        try:
            raw_key = decrypt_api_key(chatbot.custom_api_key_encrypted)
        except Exception:
            raw_key = None

    return {
        "llm_provider":         chatbot.llm_provider,
        "llm_model":            chatbot.llm_model,
        "llm_api_key":          raw_key,
        "system_prompt":        chatbot.custom_system_prompt,
        "tone_preset":          chatbot.tone_preset,
        "company_name":         company_name,
    }


def _err(code: str, message: str) -> dict:
    return {"type": "error", "code": code, "message": message}


def _utcnow():
    from datetime import datetime
    return datetime.now(timezone.utc)
