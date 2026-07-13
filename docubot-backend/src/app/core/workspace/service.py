"""
Workspace service — create, list, update, delete workspaces
and manage workspace membership (invite, accept, update role, remove).
"""

from __future__ import annotations

import uuid
from datetime import timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.data.models import User, Workspace, WorkspaceMember
from app.data.repositories.workspace_repo import (
    WorkspaceMemberRepository,
    WorkspaceRepository,
    WorkspaceInvitationRepository,
)
from app.infrastructure.email.mailer import send_workspace_invitation_email
from app.schemas.workspace import (
    AcceptInviteRequest,
    InviteMemberRequest,
    MemberOut,
    UpdateMemberRoleRequest,
    WorkspaceCreate,
    WorkspaceListOut,
    WorkspaceOut,
    WorkspaceUpdate,
)
from app.utils.exceptions import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
)
from app.utils.security import generate_secure_token, token_expiry
from app.utils.validation import make_slug


class WorkspaceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.ws_repo = WorkspaceRepository(session)
        self.mem_repo = WorkspaceMemberRepository(session)
        self.inv_repo = WorkspaceInvitationRepository(session)

    # ── Workspace CRUD ────────────────────────────────────────────────────────

    async def create(self, data: WorkspaceCreate, owner: User) -> WorkspaceOut:
        slug = data.slug or make_slug(data.name)

        # Ensure uniqueness, append short uid suffix if taken
        if await self.ws_repo.slug_exists(slug):
            slug = f"{slug}-{str(uuid.uuid4())[:8]}"

        workspace = await self.ws_repo.create(
            name=data.name,
            slug=slug,
            owner_id=owner.id,
        )

        # Owner is automatically an admin member
        await self.mem_repo.create(
            workspace_id=workspace.id,
            user_id=owner.id,
            role="admin",
            joined_at=_utcnow(),
        )

        return WorkspaceOut.model_validate(workspace)

    async def list_for_user(self, user: User) -> list[WorkspaceListOut]:
        rows = await self.ws_repo.list_for_user(user.id)
        result = []
        for row in rows:
            ws = row["workspace"]
            out = WorkspaceListOut(
                id=ws.id,
                name=ws.name,
                slug=ws.slug,
                plan_tier=ws.plan_tier,
                role=row["role"],
                chatbot_count=row["chatbot_count"],
                created_at=ws.created_at,
            )
            result.append(out)
        return result

    async def get(
        self, workspace_id: uuid.UUID, user: User
    ) -> WorkspaceOut:
        ws = await self._require_workspace(workspace_id)
        await self._require_member(workspace_id, user.id)
        return WorkspaceOut.model_validate(ws)

    async def update(
        self, workspace_id: uuid.UUID, data: WorkspaceUpdate, user: User
    ) -> WorkspaceOut:
        ws = await self._require_workspace(workspace_id)
        await self._require_role(workspace_id, user.id, min_role="admin")

        updates: dict = {}
        if data.name is not None:
            updates["name"] = data.name
        if data.settings is not None:
            updates["settings"] = {**ws.settings, **data.settings}

        ws = await self.ws_repo.update(ws, **updates)
        return WorkspaceOut.model_validate(ws)

    async def delete(self, workspace_id: uuid.UUID, user: User) -> None:
        ws = await self._require_workspace(workspace_id)
        if ws.owner_id != user.id:
            raise ForbiddenError("Only the workspace owner can delete it.")
        await self.ws_repo.soft_delete(ws)

    # ── Member management ─────────────────────────────────────────────────────

    async def list_members(
        self, workspace_id: uuid.UUID, user: User
    ) -> list[MemberOut]:
        await self._require_member(workspace_id, user.id)
        rows = await self.mem_repo.list_members(workspace_id)
        return [
            MemberOut(
                id=row["member"].id,
                workspace_id=row["member"].workspace_id,
                user_id=row["member"].user_id,
                role=row["member"].role,
                email=row["email"],
                full_name=row["full_name"],
                avatar_url=row["avatar_url"],
                invited_at=row["member"].invited_at,
                joined_at=row["member"].joined_at,
            )
            for row in rows
        ]

    async def invite_member(
        self,
        workspace_id: uuid.UUID,
        data: InviteMemberRequest,
        inviter: User,
    ) -> MemberOut:
        ws = await self._require_workspace(workspace_id)
        await self._require_role(workspace_id, inviter.id, min_role="admin")

        # Look up the invitee by email
        from app.data.repositories.user_repo import UserRepository
        user_repo = UserRepository(self.session)
        invitee = await user_repo.get_by_email(data.email)

        invitation_token = generate_secure_token(32)
        invitation_expires_at = token_expiry(days=7)

        if invitee:
            # User exists, create WorkspaceMember (pending)
            existing = await self.mem_repo.get_membership(workspace_id, invitee.id)
            if existing and existing.joined_at is not None:
                raise ConflictError("This user is already a member of the workspace.")

            if existing:
                member = await self.mem_repo.update(
                    existing,
                    role=data.role,
                    invitation_token=invitation_token,
                    invitation_expires_at=invitation_expires_at,
                    invited_by=inviter.id,
                )
            else:
                member = await self.mem_repo.create(
                    workspace_id=workspace_id,
                    user_id=invitee.id,
                    role=data.role,
                    invited_by=inviter.id,
                    invitation_token=invitation_token,
                    invitation_expires_at=invitation_expires_at,
                )
            
            await send_workspace_invitation_email(
                email=invitee.email,
                token=invitation_token,
                workspace_name=ws.name,
                invited_by_name=inviter.full_name or inviter.email,
            )

            return MemberOut(
                id=member.id,
                workspace_id=member.workspace_id,
                user_id=member.user_id,
                role=member.role,
                email=invitee.email,
                full_name=invitee.full_name,
                avatar_url=invitee.avatar_url,
                invited_at=member.invited_at,
                joined_at=member.joined_at,
            )
        else:
            # User does not exist, create WorkspaceInvitation
            existing_inv = await self.inv_repo.get_by_email_workspace(data.email, workspace_id)
            if existing_inv:
                inv = await self.inv_repo.update(
                    existing_inv,
                    role=data.role,
                    invitation_token=invitation_token,
                    invitation_expires_at=invitation_expires_at,
                    invited_by=inviter.id,
                )
            else:
                inv = await self.inv_repo.create(
                    workspace_id=workspace_id,
                    email=data.email,
                    role=data.role,
                    invited_by=inviter.id,
                    invitation_token=invitation_token,
                    invitation_expires_at=invitation_expires_at,
                )

            await send_workspace_invitation_email(
                email=data.email,
                token=invitation_token,
                workspace_name=ws.name,
                invited_by_name=inviter.full_name or inviter.email,
            )

            return MemberOut(
                id=inv.id,
                workspace_id=inv.workspace_id,
                user_id=None,
                role=inv.role,
                email=inv.email,
                full_name=None,
                avatar_url=None,
                invited_at=inv.invited_at,
                joined_at=None,
            )

    async def accept_invitation(
        self, data: AcceptInviteRequest, user: User
    ) -> MemberOut:
        member = await self.mem_repo.get_by_invitation_token(data.token)
        if not member:
            raise BadRequestError("Invalid or expired invitation token.")

        if member.user_id != user.id:
            raise ForbiddenError("This invitation was sent to a different account.")

        expires = member.invitation_expires_at
        if expires and expires.replace(tzinfo=timezone.utc) < _utcnow():
            raise BadRequestError("Invitation has expired. Please ask to be re-invited.")

        member = await self.mem_repo.accept_invitation(member)

        # Load user details for response
        from app.data.repositories.user_repo import UserRepository
        invitee = await UserRepository(self.session).get_by_id(user.id)

        return MemberOut(
            id=member.id,
            workspace_id=member.workspace_id,
            user_id=member.user_id,
            role=member.role,
            email=user.email,
            full_name=user.full_name,
            avatar_url=user.avatar_url,
            invited_at=member.invited_at,
            joined_at=member.joined_at,
        )

    async def update_member_role(
        self,
        workspace_id: uuid.UUID,
        target_user_id: uuid.UUID,
        data: UpdateMemberRoleRequest,
        actor: User,
    ) -> MemberOut:
        ws = await self._require_workspace(workspace_id)
        await self._require_role(workspace_id, actor.id, min_role="admin")

        if target_user_id == ws.owner_id:
            raise ForbiddenError("Cannot change the role of the workspace owner.")

        member = await self.mem_repo.get_membership(workspace_id, target_user_id)
        if not member or member.joined_at is None:
            raise NotFoundError("WorkspaceMember")

        member = await self.mem_repo.update(member, role=data.role)

        from app.data.repositories.user_repo import UserRepository
        target = await UserRepository(self.session).get_by_id(target_user_id)

        return MemberOut(
            id=member.id,
            workspace_id=member.workspace_id,
            user_id=member.user_id,
            role=member.role,
            email=target.email if target else "",
            full_name=target.full_name if target else None,
            avatar_url=target.avatar_url if target else None,
            invited_at=member.invited_at,
            joined_at=member.joined_at,
        )

    async def remove_member(
        self,
        workspace_id: uuid.UUID,
        target_user_id: uuid.UUID,
        actor: User,
    ) -> None:
        ws = await self._require_workspace(workspace_id)

        if target_user_id == ws.owner_id:
            raise ForbiddenError("Cannot remove the workspace owner.")

        # Members can remove themselves; admins can remove anyone
        if actor.id != target_user_id:
            await self._require_role(workspace_id, actor.id, min_role="admin")

        member = await self.mem_repo.get_membership(workspace_id, target_user_id)
        if not member:
            raise NotFoundError("WorkspaceMember")

        await self.mem_repo.delete(member)

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _require_workspace(self, workspace_id: uuid.UUID) -> Workspace:
        ws = await self.ws_repo.get_by_id_active(workspace_id)
        if not ws:
            raise NotFoundError("Workspace")
        return ws

    async def _require_member(
        self, workspace_id: uuid.UUID, user_id: uuid.UUID
    ) -> WorkspaceMember:
        member = await self.mem_repo.get_membership(workspace_id, user_id)
        if not member or member.joined_at is None:
            raise ForbiddenError("You are not a member of this workspace.")
        return member

    async def _require_role(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        min_role: str,
    ) -> WorkspaceMember:
        """Assert the user has at least `min_role` in the workspace."""
        _ROLE_RANK = {"viewer": 0, "editor": 1, "admin": 2, "owner": 3}
        member = await self._require_member(workspace_id, user_id)
        ws = await self.ws_repo.get_by_id_active(workspace_id)
        effective_role = "owner" if ws and ws.owner_id == user_id else member.role
        if _ROLE_RANK.get(effective_role, -1) < _ROLE_RANK.get(min_role, 99):
            raise ForbiddenError(
                f"This action requires at least the '{min_role}' role."
            )
        return member


def _utcnow():
    from datetime import datetime
    return datetime.now(timezone.utc)