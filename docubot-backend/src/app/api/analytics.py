"""Analytics endpoints — Phase 6."""

import uuid
from typing import Optional

from fastapi import APIRouter, Query

from app.api.dependencies import DbSession, VerifiedUser
from app.core.analytics.service import AnalyticsService
from app.schemas.analytics import AnalyticsDashboard

router = APIRouter(prefix="/workspaces/{workspace_id}/metrics", tags=["analytics"])


@router.get(
    "",
    response_model=AnalyticsDashboard,
    summary="Get analytics dashboard for a workspace",
)
async def get_dashboard(
    workspace_id: uuid.UUID,
    user: VerifiedUser,
    session: DbSession,
    chatbot_id: Optional[uuid.UUID] = Query(default=None),
    days: int = Query(default=30, ge=1, le=365),
) -> AnalyticsDashboard:
    return await AnalyticsService(session).get_dashboard(
        workspace_id, user.id, chatbot_id, days
    )