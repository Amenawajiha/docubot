"""
FastAPI dependency injectors.

Type aliases (CurrentUser, VerifiedUser, DbSession, WorkspaceMember)
let route functions declare their requirements cleanly:

    async def my_route(
        user: VerifiedUser,
        session: DbSession,
        workspace_id: uuid.UUID,
    ) -> ...:
        ...
"""

from __future__ import annotations

import logging
import uuid
from typing import Annotated

from fastapi import Depends, Path, Security, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.service import get_user_from_token
from app.data.database import get_db
from app.data.models import User, WorkspaceMember
from app.data.repositories.workspace_repo import WorkspaceMemberRepository
from app.utils.exceptions import ForbiddenError

_log = logging.getLogger(__name__)
_bearer = HTTPBearer(auto_error=False)


# ── Auth dependencies ─────────────────────────────────────────────────────────

async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(_bearer)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    token: str | None = request.cookies.get("access_token")
    if not token and credentials:
        token = credentials.credentials

    if not token:
        from app.utils.exceptions import UnauthorizedError
        raise UnauthorizedError("Not authenticated")

    try:
        return await get_user_from_token(token, session)
    except Exception as e:
        _log.warning(f"Auth fail in get_current_user: {e}")
        raise


async def require_verified(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    from app.utils.exceptions import EmailNotVerifiedError
    if not user.email_verified:
        raise EmailNotVerifiedError()
    return user


# ── Workspace membership dependencies ────────────────────────────────────────

async def get_workspace_member(
    workspace_id: Annotated[uuid.UUID, Path()],
    user: Annotated[User, Depends(require_verified)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> WorkspaceMember:
    """Resolve the calling user's membership in the requested workspace.
    Raises 403 if they are not a member or haven't accepted the invitation."""
    repo = WorkspaceMemberRepository(session)
    member = await repo.get_membership(workspace_id, user.id)
    if not member or member.joined_at is None:
        _log.warning(f"Workspace membership check fail for user {user.id} on workspace {workspace_id}")
        raise ForbiddenError("You are not a member of this workspace.")
    return member


async def require_admin(
    member: Annotated[WorkspaceMember, Depends(get_workspace_member)],
    workspace_id: Annotated[uuid.UUID, Path()],
    user: Annotated[User, Depends(require_verified)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> WorkspaceMember:
    """Require at least admin role (or owner)."""
    from app.data.repositories.workspace_repo import WorkspaceRepository
    ws = await WorkspaceRepository(session).get_by_id_active(workspace_id)
    if ws and ws.owner_id == user.id:
        return member
    if member.role not in ("admin",):
        raise ForbiddenError("This action requires admin role.")
    return member


# ── Convenience type aliases ──────────────────────────────────────────────────

CurrentUser    = Annotated[User, Depends(get_current_user)]
VerifiedUser   = Annotated[User, Depends(require_verified)]
DbSession      = Annotated[AsyncSession, Depends(get_db)]
WorkspaceMembership = Annotated[WorkspaceMember, Depends(get_workspace_member)]
WorkspaceAdmin = Annotated[WorkspaceMember, Depends(require_admin)]