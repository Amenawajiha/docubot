"""
DashboardService — composes workspace overview data from multiple domains.

Single responsibility: aggregate and return the data the frontend needs to
render the Workspace Overview page in one request.

This service is intentionally read-only and has no business logic of its own.
It delegates every data concern to the appropriate repository:

    DashboardService
    ├── WorkspaceRepository          → active bot count
    ├── AnalyticsDailyRepository     → total_conversations, satisfaction_rate
    ├── DocumentRepository           → total completed documents
    └── DeploymentChannelRepository  → any active deployment channel exists

Nothing here belongs in AnalyticsService (which tracks events and rollups),
WorkspaceService (which manages workspace lifecycle), or any other domain
service. This is a pure composition layer.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.models import (
    AnalyticsDaily,
    Chatbot,
    ChatbotDocument,
    DeploymentChannel,
)
from app.data.repositories.workspace_repo import WorkspaceMemberRepository
from app.schemas.dashboard import (
    DashboardChecklistOut,
    DashboardMetricsOut,
    DashboardOut,
)
from app.utils.exceptions import ForbiddenError

# Total number of checklist steps — used to compute progress percent.
_CHECKLIST_STEPS = 4


class DashboardService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._mem_repo = WorkspaceMemberRepository(db)

    async def get_dashboard(
        self,
        workspace_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> DashboardOut:
        await self._require_member(workspace_id, actor_id)

        # Run all four queries concurrently via gather
        import asyncio

        (
            (active_bots, total_bots),
            (total_conversations, satisfaction_rate, avg_response_time),
            total_documents,
            has_deployments,
        ) = await asyncio.gather(
            self._count_bots(workspace_id),
            self._get_conversation_stats(workspace_id),
            self._count_completed_documents(workspace_id),
            self._has_active_deployment(workspace_id),
        )

        checklist = DashboardChecklistOut(
            has_chatbot=total_bots > 0,
            has_documents=total_documents > 0,
            has_deployments=has_deployments,
            has_conversations=total_conversations > 0,
        )

        completed = sum([
            checklist.has_chatbot,
            checklist.has_documents,
            checklist.has_deployments,
            checklist.has_conversations,
        ])
        # Round to nearest 25 so the progress bar snaps to clean steps
        progress = round((completed / _CHECKLIST_STEPS) * 100 / 25) * 25

        metrics = DashboardMetricsOut(
            active_bots=active_bots,
            total_conversations=total_conversations,
            satisfaction_rate=satisfaction_rate,
            total_documents=total_documents,
            avg_response_time=avg_response_time,
        )

        return DashboardOut(
            metrics=metrics,
            checklist=checklist,
            setup_progress_percent=progress,
        )

    # ── Private query methods — one per data concern ──────────────────────────

    async def _count_bots(self, workspace_id: uuid.UUID) -> tuple[int, int]:
        """
        Count chatbots in this workspace. Returns (active_bots, total_bots).
        active_bots: deployment_status == "published"
        Source: chatbots table
        """
        result = await self._db.execute(
            select(
                func.count(Chatbot.id).filter(Chatbot.deployment_status == "published"),
                func.count(Chatbot.id)
            ).where(
                Chatbot.workspace_id == workspace_id,
                Chatbot.deleted_at.is_(None),
            )
        )
        row = result.one()
        return row[0], row[1]

    async def _get_conversation_stats(
        self, workspace_id: uuid.UUID
    ) -> tuple[int, float | None, str | None]:
        """
        Return (total_sessions, avg_confidence, avg_response_time) aggregated across all time
        and all chatbots in this workspace.

        Source: analytics_daily rollup — owned by the analytics domain.
        Using the pre-aggregated table avoids a full scan of chat_sessions.
        """
        result = await self._db.execute(
            select(
                func.coalesce(func.sum(AnalyticsDaily.total_sessions), 0).label("sessions"),
                func.avg(AnalyticsDaily.avg_confidence).label("confidence"),
                func.avg(AnalyticsDaily.avg_response_time_ms).label("response_time"),
            ).where(
                AnalyticsDaily.workspace_id == workspace_id,
            )
        )
        row = result.one()
        sessions    = int(row.sessions)
        confidence  = float(row.confidence) if row.confidence else None
        
        response_time = None
        if row.response_time:
            # Format to seconds with 1 decimal place (e.g. 1.2s)
            response_time = f"{float(row.response_time) / 1000:.1f}s"
            
        return sessions, confidence, response_time

    async def _count_completed_documents(self, workspace_id: uuid.UUID) -> int:
        """
        Count documents with upload_status == "completed" across the workspace.

        Source: chatbot_documents table — owned by the knowledge domain.
        Workspace-wide (not per-chatbot) because the checklist question is
        "has this workspace indexed any knowledge at all".
        """
        result = await self._db.execute(
            select(func.count(ChatbotDocument.id)).where(
                ChatbotDocument.workspace_id == workspace_id,
                ChatbotDocument.upload_status == "completed",
                ChatbotDocument.deleted_at.is_(None),
            )
        )
        return result.scalar_one()

    async def _has_active_deployment(self, workspace_id: uuid.UUID) -> bool:
        """
        Return True if at least one active deployment channel exists anywhere
        in this workspace.

        Source: deployment_channels table — owned by the deployment domain.
        """
        result = await self._db.execute(
            select(func.count(DeploymentChannel.id)).where(
                DeploymentChannel.workspace_id == workspace_id,
                DeploymentChannel.is_active.is_(True),
            )
        )
        return result.scalar_one() > 0

    async def _require_member(
        self, workspace_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        member = await self._mem_repo.get_membership(workspace_id, user_id)
        if not member or member.joined_at is None:
            raise ForbiddenError("You are not a member of this workspace.")