"""
Repositories for Phase 4/5 — chat sessions, messages, usage logs.
All queries are hard-scoped to (workspace_id, chatbot_id).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.models import ChatMessage, ChatSession, InternalApiKey, WorkspaceUsageLog
from app.data.repositories.base import BaseRepository


class ChatSessionRepository(BaseRepository[ChatSession]):
    model = ChatSession

    async def get_by_token(self, token: str) -> ChatSession | None:
        result = await self.session.execute(
            select(ChatSession).where(ChatSession.session_token == token)
        )
        return result.scalar_one_or_none()

    async def get_active_by_id(
        self,
        session_id: uuid.UUID,
        workspace_id: uuid.UUID,
        chatbot_id: uuid.UUID,
    ) -> ChatSession | None:
        result = await self.session.execute(
            select(ChatSession).where(
                ChatSession.id == session_id,
                ChatSession.workspace_id == workspace_id,
                ChatSession.chatbot_id == chatbot_id,
                ChatSession.session_status == "active",
            )
        )
        return result.scalar_one_or_none()

    async def end_session(
        self, session: ChatSession, summary: str | None = None
    ) -> ChatSession:
        now = datetime.now(timezone.utc)
        duration = int((now - session.created_at.replace(tzinfo=timezone.utc)).total_seconds())
        return await self.update(
            session,
            session_status="ended",
            ended_at=now,
            duration_seconds=duration,
            session_summary=summary,
        )

    async def increment_message_count(
        self, session: ChatSession, tokens: int
    ) -> ChatSession:
        return await self.update(
            session,
            message_count=session.message_count + 1,
            total_tokens=session.total_tokens + tokens,
            updated_at=datetime.now(timezone.utc),
        )

    async def get_total_messages_for_end_user(
        self, chatbot_id: uuid.UUID, end_user_id: str
    ) -> int:
        result = await self.session.execute(
            select(func.sum(ChatSession.message_count)).where(
                ChatSession.chatbot_id == chatbot_id,
                ChatSession.end_user_id == end_user_id,
            )
        )
        return result.scalar() or 0



class ChatMessageRepository(BaseRepository[ChatMessage]):
    model = ChatMessage

    async def list_for_session(
        self,
        session_id: uuid.UUID,
        workspace_id: uuid.UUID,
        chatbot_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ChatMessage]:
        result = await self.session.execute(
            select(ChatMessage)
            .where(
                ChatMessage.session_id == session_id,
                ChatMessage.workspace_id == workspace_id,
                ChatMessage.chatbot_id == chatbot_id,
            )
            .order_by(ChatMessage.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_recent_for_session(
        self, session_id: uuid.UUID, limit: int = 20
    ) -> list[ChatMessage]:
        """Return the N most recent messages — used for conversation history context."""
        result = await self.session.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
        return list(reversed(result.scalars().all()))

    async def purge_old_messages_for_session(
        self, session_id: uuid.UUID, keep_recent: int = 10
    ) -> int:
        """
        Delete older messages for a given session while keeping the most recent N messages.
        Returns number of deleted messages.
        """
        result = await self.session.execute(
            select(ChatMessage.id)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .offset(keep_recent)
        )
        old_ids = list(result.scalars().all())
        if not old_ids:
            return 0
        del_res = await self.session.execute(
            delete(ChatMessage).where(ChatMessage.id.in_(old_ids))
        )
        await self.session.commit()
        return del_res.rowcount or len(old_ids)

    async def insert_summary_message(
        self,
        workspace_id: uuid.UUID,
        chatbot_id: uuid.UUID,
        session_id: uuid.UUID,
        end_user_id: str | None,
        summary_text: str,
    ) -> ChatMessage:
        """Insert a summarized representation of older conversation turns before existing messages."""
        recent_res = await self.session.execute(
            select(ChatMessage.created_at)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
            .limit(1)
        )
        oldest_dt = recent_res.scalar_one_or_none()
        summary_dt = (oldest_dt - timedelta(seconds=1)) if oldest_dt else datetime.now(timezone.utc)

        return await self.create(
            workspace_id=workspace_id,
            chatbot_id=chatbot_id,
            session_id=session_id,
            end_user_id=end_user_id,
            role="assistant",
            content=f"[Conversation Summary]: {summary_text}",
            created_at=summary_dt,
            metadata_={"is_summary": True},
        )


class UsageLogRepository(BaseRepository[WorkspaceUsageLog]):
    model = WorkspaceUsageLog

    async def log_usage(
        self,
        workspace_id: uuid.UUID,
        chatbot_id: uuid.UUID,
        session_id: uuid.UUID,
        tokens_input: int,
        tokens_output: int,
        cost_usd: float,
    ) -> WorkspaceUsageLog:
        return await self.create(
            workspace_id=workspace_id,
            chatbot_id=chatbot_id,
            session_id=session_id,
            log_date=datetime.now(timezone.utc).date(),
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            tokens_total=tokens_input + tokens_output,
            cost_usd=str(cost_usd),
            message_count=1,
        )

    async def get_monthly_usage(
        self,
        workspace_id: uuid.UUID,
        year: int,
        month: int,
    ) -> dict:
        """Aggregate token usage for a workspace in a given month."""
        from sqlalchemy import extract
        result = await self.session.execute(
            select(
                func.sum(WorkspaceUsageLog.tokens_total).label("tokens"),
                func.sum(WorkspaceUsageLog.cost_usd).label("cost"),
                func.sum(WorkspaceUsageLog.message_count).label("messages"),
            ).where(
                WorkspaceUsageLog.workspace_id == workspace_id,
                extract("year",  WorkspaceUsageLog.log_date) == year,
                extract("month", WorkspaceUsageLog.log_date) == month,
            )
        )
        row = result.one()
        return {
            "tokens_total":    int(row.tokens  or 0),
            "cost_usd":        float(row.cost  or 0),
            "message_count":   int(row.messages or 0),
        }

    async def check_monthly_quota(
        self,
        workspace_id: uuid.UUID,
        monthly_limit: int,
    ) -> dict:
        """Return current-month usage vs limit."""
        now = datetime.now(timezone.utc)
        usage = await self.get_monthly_usage(workspace_id, now.year, now.month)
        tokens_used = usage["tokens_total"]
        remaining   = max(0, monthly_limit - tokens_used)
        return {
            "allowed":         remaining > 0,
            "current_usage":   tokens_used,
            "limit":           monthly_limit,
            "remaining_tokens": remaining,
            "reason":          None if remaining > 0 else "Monthly token quota exceeded.",
        }


class InternalApiKeyRepository(BaseRepository[InternalApiKey]):
    model = InternalApiKey

    async def get_by_prefix(self, prefix: str) -> InternalApiKey | None:
        result = await self.session.execute(
            select(InternalApiKey).where(
                InternalApiKey.key_prefix == prefix,
                InternalApiKey.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def touch_last_used(self, key: InternalApiKey) -> None:
        await self.update(key, last_used_at=datetime.now(timezone.utc))