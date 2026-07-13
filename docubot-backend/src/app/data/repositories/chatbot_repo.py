"""Chatbot repository — all DB access for the chatbots table."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.models import Chatbot
from app.data.repositories.base import BaseRepository


class ChatbotRepository(BaseRepository[Chatbot]):
    model = Chatbot

    async def get_by_id_in_workspace(
        self, chatbot_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> Chatbot | None:
        """Fetch a chatbot only if it belongs to the given workspace and is not deleted."""
        result = await self.session.execute(
            select(Chatbot).where(
                Chatbot.id == chatbot_id,
                Chatbot.workspace_id == workspace_id,
                Chatbot.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_for_workspace(
        self, workspace_id: uuid.UUID, *, include_archived: bool = False
    ) -> list[Chatbot]:
        stmt = select(Chatbot).where(
            Chatbot.workspace_id == workspace_id,
            Chatbot.deleted_at.is_(None),
        )
        if not include_archived:
            stmt = stmt.where(Chatbot.deployment_status != "archived")
        stmt = stmt.order_by(Chatbot.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_active_for_workspace(self, workspace_id: uuid.UUID) -> int:
        from sqlalchemy import func
        result = await self.session.execute(
            select(func.count(Chatbot.id)).where(
                Chatbot.workspace_id == workspace_id,
                Chatbot.deleted_at.is_(None),
                Chatbot.deployment_status != "archived",
            )
        )
        return result.scalar_one()

    async def soft_delete(self, chatbot: Chatbot) -> Chatbot:
        return await self.update(
            chatbot,
            deleted_at=datetime.now(timezone.utc),
            is_active=False,
            deployment_status="archived",
        )