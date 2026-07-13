"""
Workspace + WorkspaceMember repository.

All soft-delete filtering is applied here so callers never see
deleted workspaces unless they explicitly query for them.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.data.models import Chatbot, User, Workspace, WorkspaceMember, WorkspaceInvitation
from app.data.repositories.base import BaseRepository


class WorkspaceRepository(BaseRepository[Workspace]):
    model = Workspace

    # ── Queries ───────────────────────────────────────────────────────────────

    async def get_by_id_active(self, workspace_id: uuid.UUID) -> Workspace | None:
        """Get workspace only if not soft-deleted."""
        result = await self.session.execute(
            select(Workspace).where(
                Workspace.id == workspace_id,
                Workspace.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Workspace | None:
        result = await self.session.execute(
            select(Workspace).where(
                Workspace.slug == slug,
                Workspace.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def slug_exists(self, slug: str, exclude_id: uuid.UUID | None = None) -> bool:
        stmt = select(Workspace.id).where(Workspace.slug == slug)
        if exclude_id:
            stmt = stmt.where(Workspace.id != exclude_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def list_for_user(self, user_id: uuid.UUID) -> list[dict]:
        """
        Return all active workspaces the user owns or is a member of,
        along with their role and chatbot count.
        """
        # Workspaces the user owns
        owned = await self.session.execute(
            select(Workspace).where(
                Workspace.owner_id == user_id,
                Workspace.deleted_at.is_(None),
            )
        )
        owned_workspaces = owned.scalars().all()

        # Workspaces via membership
        member_q = await self.session.execute(
            select(WorkspaceMember, Workspace)
            .join(Workspace, WorkspaceMember.workspace_id == Workspace.id)
            .where(
                WorkspaceMember.user_id == user_id,
                WorkspaceMember.joined_at.is_not(None),
                Workspace.deleted_at.is_(None),
                Workspace.owner_id != user_id,   # don't double-count owned
            )
        )
        member_rows = member_q.all()

        results: list[dict] = []

        for ws in owned_workspaces:
            count = await self._chatbot_count(ws.id)
            results.append({
                "workspace": ws,
                "role": "owner",
                "chatbot_count": count,
            })

        for member, ws in member_rows:
            count = await self._chatbot_count(ws.id)
            results.append({
                "workspace": ws,
                "role": member.role,
                "chatbot_count": count,
            })

        return results

    async def get_chatbot_count(self, workspace_id: uuid.UUID) -> int:
        return await self._chatbot_count(workspace_id)

    async def _chatbot_count(self, workspace_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(func.count(Chatbot.id)).where(
                Chatbot.workspace_id == workspace_id,
                Chatbot.deleted_at.is_(None),
            )
        )
        return result.scalar_one()

    # ── Mutations ─────────────────────────────────────────────────────────────

    async def soft_delete(self, workspace: Workspace) -> Workspace:
        return await self.update(workspace, deleted_at=datetime.now(timezone.utc))


class WorkspaceMemberRepository(BaseRepository[WorkspaceMember]):
    model = WorkspaceMember

    async def get_membership(
        self, workspace_id: uuid.UUID, user_id: uuid.UUID
    ) -> WorkspaceMember | None:
        result = await self.session.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_invitation_token(self, token: str) -> WorkspaceMember | None:
        result = await self.session.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.invitation_token == token
            )
        )
        return result.scalar_one_or_none()

    async def list_members(self, workspace_id: uuid.UUID) -> list[dict]:
        """Return members with their user details joined."""
        result = await self.session.execute(
            select(WorkspaceMember, User)
            .join(User, WorkspaceMember.user_id == User.id)
            .where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.joined_at.is_not(None),
            )
            .order_by(WorkspaceMember.joined_at)
        )
        return [
            {
                "member": m,
                "email": u.email,
                "full_name": u.full_name,
                "avatar_url": u.avatar_url,
            }
            for m, u in result.all()
        ]

    async def list_pending_invitations(
        self, workspace_id: uuid.UUID
    ) -> list[WorkspaceMember]:
        result = await self.session.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.joined_at.is_(None),
                WorkspaceMember.invitation_token.is_not(None),
            )
        )
        return list(result.scalars().all())

    async def accept_invitation(
        self, member: WorkspaceMember
    ) -> WorkspaceMember:
        return await self.update(
            member,
            joined_at=datetime.now(timezone.utc),
            invitation_token=None,
            invitation_expires_at=None,
        )


class WorkspaceInvitationRepository(BaseRepository[WorkspaceInvitation]):
    model = WorkspaceInvitation

    async def get_by_email_workspace(
        self, email: str, workspace_id: uuid.UUID
    ) -> WorkspaceInvitation | None:
        result = await self.session.execute(
            select(WorkspaceInvitation).where(
                WorkspaceInvitation.email == email,
                WorkspaceInvitation.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_token(self, token: str) -> WorkspaceInvitation | None:
        result = await self.session.execute(
            select(WorkspaceInvitation).where(
                WorkspaceInvitation.invitation_token == token
            )
        )
        return result.scalar_one_or_none()

    async def list_pending(self, workspace_id: uuid.UUID) -> list[WorkspaceInvitation]:
        result = await self.session.execute(
            select(WorkspaceInvitation).where(
                WorkspaceInvitation.workspace_id == workspace_id
            )
        )
        return list(result.scalars().all())