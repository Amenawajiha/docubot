"""
Dashboard endpoint — Workspace Overview page.

Single endpoint: GET /workspaces/{workspace_id}/dashboard

Returns a composed payload from multiple domains in one request.
The heavy lifting is in DashboardService, not here.
"""

import uuid

from fastapi import APIRouter

from app.api.dependencies import DbSession, VerifiedUser
from app.core.dashboard.service import DashboardService
from app.schemas.dashboard import DashboardOut

router = APIRouter(prefix="/workspaces/{workspace_id}/dashboard", tags=["dashboard"])


@router.get(
    "",
    response_model=DashboardOut,
    summary="Workspace Overview Dashboard",
    description=(
        "Returns composed workspace-wide metrics (active bots, conversations, "
        "satisfaction rate, total documents), a Getting Started checklist, and "
        "a setup progress percentage. All data is fetched in a single request "
        "using concurrent queries to each domain's repository."
    ),
)
async def get_dashboard(
    workspace_id: uuid.UUID,
    user: VerifiedUser,
    session: DbSession,
) -> DashboardOut:
    return await DashboardService(session).get_dashboard(workspace_id, user.id)