"""Analytics service — Phase 6."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.data.repositories.analytics_repo import (
    AnalyticsDailyRepository,
    AnalyticsEventRepository,
)
from app.data.repositories.chatbot_repo import ChatbotRepository
from app.data.repositories.workspace_repo import WorkspaceMemberRepository
from app.schemas.analytics import (
    AnalyticsDashboard,
    AnalyticsSummary,
    DailyMetricOut,
    TopQuestion,
)
from app.utils.exceptions import ForbiddenError, NotFoundError


class AnalyticsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db         = db
        self.event_repo = AnalyticsEventRepository(db)
        self.daily_repo = AnalyticsDailyRepository(db)
        self.bot_repo   = ChatbotRepository(db)
        self.mem_repo   = WorkspaceMemberRepository(db)

    async def record_chat_event(
        self,
        workspace_id: uuid.UUID,
        chatbot_id: uuid.UUID,
        session_id: uuid.UUID,
        event_type: str,
        *,
        confidence: float | None = None,
        tokens_used: int = 0,
        response_time_ms: int | None = None,
        content: str | None = None,
        cost_usd: float = 0.0,
        end_user_id: str | None = None,
    ) -> None:
        """Fire-and-forget analytics recording called from the chat engine."""
        event_data: dict = {}
        if content:
            event_data["content"] = content[:500]   # cap at 500 chars

        await self.event_repo.record(
            workspace_id=workspace_id,
            chatbot_id=chatbot_id,
            event_type=event_type,
            session_id=session_id,
            event_data=event_data,
            confidence_score=confidence,
            tokens_used=tokens_used,
            response_time_ms=response_time_ms,
            end_user_id=end_user_id,
        )

        today = datetime.now(timezone.utc).date()
        is_message = event_type in ("message_sent", "message_received")
        is_session = event_type == "session_started"
        clarification = event_type == "clarification_asked"

        await self.daily_repo.upsert_daily(
            workspace_id=workspace_id,
            chatbot_id=chatbot_id,
            day=today,
            sessions_delta=1 if is_session else 0,
            messages_delta=1 if is_message else 0,
            tokens_delta=tokens_used,
            cost_delta=cost_usd,
            confidence=confidence if is_message else None,
            response_time_ms=response_time_ms if is_message else None,
            clarification=clarification,
        )

    async def get_dashboard(
        self,
        workspace_id: uuid.UUID,
        actor_id: uuid.UUID,
        chatbot_id: uuid.UUID | None = None,
        days: int = 30,
    ) -> AnalyticsDashboard:
        await self._require_member(workspace_id, actor_id)

        end   = datetime.now(timezone.utc).date()
        start = end - timedelta(days=days - 1)

        if chatbot_id:
            bot = await self.bot_repo.get_by_id_in_workspace(
                chatbot_id, workspace_id
            )
            if not bot:
                raise NotFoundError("Chatbot")

        summary_data = await self.daily_repo.get_summary(
            workspace_id, chatbot_id, start, end
        )
        unique_users = await self.event_repo.count_unique_users(
            workspace_id, chatbot_id, start, end
        )
        summary = AnalyticsSummary(
            workspace_id=workspace_id,
            chatbot_id=chatbot_id,
            period_start=start,
            period_end=end,
            unique_users=unique_users,
            **summary_data,
        )

        daily_rows = await self.daily_repo.get_range(
            workspace_id, chatbot_id, start, end
        )
        daily_metrics = [DailyMetricOut.model_validate(r) for r in daily_rows]

        since = datetime.now(timezone.utc) - timedelta(days=days)
        top_q_data: list[dict] = []
        if chatbot_id:
            top_q_data = await self.event_repo.get_top_questions(
                chatbot_id, since, limit=10
            )
        top_questions = [TopQuestion(**q) for q in top_q_data]

        return AnalyticsDashboard(
            summary=summary,
            daily_metrics=daily_metrics,
            top_questions=top_questions,
        )

    async def _require_member(
        self, workspace_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        member = await self.mem_repo.get_membership(workspace_id, user_id)
        if not member or member.joined_at is None:
            raise ForbiddenError("You are not a member of this workspace.")