"""Analytics repository — events and daily rollups."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.models import AnalyticsDaily, AnalyticsEvent
from app.data.repositories.base import BaseRepository


class AnalyticsEventRepository(BaseRepository[AnalyticsEvent]):
    model = AnalyticsEvent

    async def record(
        self,
        workspace_id: uuid.UUID,
        chatbot_id: uuid.UUID,
        event_type: str,
        *,
        session_id: uuid.UUID | None = None,
        event_data: dict | None = None,
        confidence_score: float | None = None,
        tokens_used: int = 0,
        response_time_ms: int | None = None,
        end_user_id: str | None = None,
    ) -> AnalyticsEvent:
        return await self.create(
            workspace_id=workspace_id,
            chatbot_id=chatbot_id,
            event_type=event_type,
            session_id=session_id,
            event_data=event_data or {},
            confidence_score=str(confidence_score) if confidence_score else None,
            tokens_used=tokens_used,
            response_time_ms=response_time_ms,
            end_user_id=end_user_id,
        )

    async def count_by_type(
        self,
        chatbot_id: uuid.UUID,
        event_type: str,
        since: datetime,
    ) -> int:
        result = await self.session.execute(
            select(func.count(AnalyticsEvent.id)).where(
                AnalyticsEvent.chatbot_id == chatbot_id,
                AnalyticsEvent.event_type == event_type,
                AnalyticsEvent.created_at >= since,
            )
        )
        return result.scalar_one()

    async def get_top_questions(
        self,
        chatbot_id: uuid.UUID,
        since: datetime,
        limit: int = 10,
    ) -> list[dict]:
        """Return top user messages by frequency."""
        result = await self.session.execute(
            select(
                AnalyticsEvent.event_data["content"].astext.label("content"),
                func.count(AnalyticsEvent.id).label("count"),
                func.avg(AnalyticsEvent.confidence_score).label("avg_confidence"),
            )
            .where(
                AnalyticsEvent.chatbot_id == chatbot_id,
                AnalyticsEvent.event_type == "message_sent",
                AnalyticsEvent.created_at >= since,
            )
            .group_by(text("content"))
            .order_by(text("count DESC"))
            .limit(limit)
        )
        return [
            {"content": r.content, "count": r.count,
             "avg_confidence": float(r.avg_confidence) if r.avg_confidence else None}
            for r in result.all()
        ]

    async def count_unique_users(
        self,
        workspace_id: uuid.UUID,
        chatbot_id: uuid.UUID | None,
        start: date,
        end: date,
    ) -> int:
        stmt = select(func.count(func.distinct(AnalyticsEvent.end_user_id))).where(
            AnalyticsEvent.workspace_id == workspace_id,
            func.date(AnalyticsEvent.created_at) >= start,
            func.date(AnalyticsEvent.created_at) <= end,
            AnalyticsEvent.end_user_id.is_not(None),
        )
        if chatbot_id:
            stmt = stmt.where(AnalyticsEvent.chatbot_id == chatbot_id)
        result = await self.session.execute(stmt)
        return result.scalar_one() or 0



class AnalyticsDailyRepository(BaseRepository[AnalyticsDaily]):
    model = AnalyticsDaily

    async def upsert_daily(
        self,
        workspace_id: uuid.UUID,
        chatbot_id: uuid.UUID,
        day: date,
        *,
        sessions_delta: int = 0,
        messages_delta: int = 0,
        tokens_delta: int = 0,
        cost_delta: float = 0.0,
        confidence: float | None = None,
        response_time_ms: int | None = None,
        clarification: bool = False,
        resolved: bool = False,
    ) -> AnalyticsDaily:
        existing = await self.session.execute(
            select(AnalyticsDaily).where(
                AnalyticsDaily.workspace_id == workspace_id,
                AnalyticsDaily.chatbot_id  == chatbot_id,
                AnalyticsDaily.date        == day,
            )
        )
        row = existing.scalar_one_or_none()

        if row:
            updates: dict = {
                "total_sessions":  row.total_sessions  + sessions_delta,
                "total_messages":  row.total_messages  + messages_delta,
                "total_tokens":    row.total_tokens    + tokens_delta,
                "total_cost_usd":  float(row.total_cost_usd) + cost_delta,
                "updated_at":      datetime.now(timezone.utc),
            }
            if confidence is not None:
                old = float(row.avg_confidence) if row.avg_confidence else confidence
                updates["avg_confidence"] = str((old + confidence) / 2)
            if response_time_ms is not None:
                old_rt = row.avg_response_time_ms or response_time_ms
                updates["avg_response_time_ms"] = int((old_rt + response_time_ms) / 2)
            return await self.update(row, **updates)

        return await self.create(
            workspace_id=workspace_id,
            chatbot_id=chatbot_id,
            date=day,
            total_sessions=sessions_delta,
            total_messages=messages_delta,
            total_tokens=tokens_delta,
            total_cost_usd=str(cost_delta),
            avg_confidence=str(confidence) if confidence else None,
            avg_response_time_ms=response_time_ms,
        )

    async def get_range(
        self,
        workspace_id: uuid.UUID,
        chatbot_id: uuid.UUID | None,
        start: date,
        end: date,
    ) -> list[AnalyticsDaily]:
        stmt = select(AnalyticsDaily).where(
            AnalyticsDaily.workspace_id == workspace_id,
            AnalyticsDaily.date >= start,
            AnalyticsDaily.date <= end,
        )
        if chatbot_id:
            stmt = stmt.where(AnalyticsDaily.chatbot_id == chatbot_id)
        stmt = stmt.order_by(AnalyticsDaily.date.asc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_summary(
        self,
        workspace_id: uuid.UUID,
        chatbot_id: uuid.UUID | None,
        start: date,
        end: date,
    ) -> dict:
        stmt = select(
            func.sum(AnalyticsDaily.total_sessions).label("sessions"),
            func.sum(AnalyticsDaily.total_messages).label("messages"),
            func.sum(AnalyticsDaily.total_tokens).label("tokens"),
            func.sum(AnalyticsDaily.total_cost_usd).label("cost"),
            func.avg(AnalyticsDaily.avg_confidence).label("confidence"),
            func.avg(AnalyticsDaily.avg_response_time_ms).label("response_time"),
            func.avg(AnalyticsDaily.clarification_rate).label("clarification_rate"),
            func.avg(AnalyticsDaily.resolution_rate).label("resolution_rate"),
        ).where(
            AnalyticsDaily.workspace_id == workspace_id,
            AnalyticsDaily.date >= start,
            AnalyticsDaily.date <= end,
        )
        if chatbot_id:
            stmt = stmt.where(AnalyticsDaily.chatbot_id == chatbot_id)
        result = await self.session.execute(stmt)
        row = result.one()
        return {
            "total_sessions":       int(row.sessions     or 0),
            "total_messages":       int(row.messages     or 0),
            "total_tokens":         int(row.tokens       or 0),
            "total_cost_usd":       float(row.cost       or 0),
            "avg_confidence":       float(row.confidence or 0) or None,
            "avg_response_time_ms": int(row.response_time or 0) or None,
            "clarification_rate":   float(row.clarification_rate or 0) or None,
            "resolution_rate":      float(row.resolution_rate    or 0) or None,
        }