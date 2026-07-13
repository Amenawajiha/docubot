"""
Workspace endpoints.

All routes require a verified user (email confirmed).
Role enforcement is handled inside WorkspaceService.
"""

import uuid

from fastapi import APIRouter, status

from app.api.dependencies import DbSession, VerifiedUser
from app.core.workspace.service import WorkspaceService
from app.core.knowledge.service import KnowledgeService
from app.schemas.auth import MessageResponse
from app.schemas.knowledge import DocumentOut
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

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


def _svc(session: DbSession) -> WorkspaceService:
    return WorkspaceService(session)


# ── Workspace CRUD ────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=WorkspaceOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new workspace",
)
async def create_workspace(
    data: WorkspaceCreate,
    user: VerifiedUser,
    session: DbSession,
) -> WorkspaceOut:
    return await _svc(session).create(data, user)


@router.get(
    "",
    response_model=list[WorkspaceListOut],
    summary="List all workspaces the current user belongs to",
)
async def list_workspaces(
    user: VerifiedUser,
    session: DbSession,
) -> list[WorkspaceListOut]:
    return await _svc(session).list_for_user(user)


@router.get(
    "/{workspace_id}/documents",
    response_model=list[DocumentOut],
    summary="List all documents in the workspace",
)
async def list_workspace_documents(
    workspace_id: uuid.UUID,
    user: VerifiedUser,
    session: DbSession,
) -> list[DocumentOut]:
    return await KnowledgeService(session).list_documents_for_workspace(workspace_id, user)



@router.get(
    "/{workspace_id}",
    response_model=WorkspaceOut,
    summary="Get workspace details",
)
async def get_workspace(
    workspace_id: uuid.UUID,
    user: VerifiedUser,
    session: DbSession,
) -> WorkspaceOut:
    return await _svc(session).get(workspace_id, user)


@router.patch(
    "/{workspace_id}",
    response_model=WorkspaceOut,
    summary="Update workspace name or settings (admin only)",
)
async def update_workspace(
    workspace_id: uuid.UUID,
    data: WorkspaceUpdate,
    user: VerifiedUser,
    session: DbSession,
) -> WorkspaceOut:
    return await _svc(session).update(workspace_id, data, user)


@router.delete(
    "/{workspace_id}",
    response_model=MessageResponse,
    summary="Soft-delete a workspace (owner only)",
)
async def delete_workspace(
    workspace_id: uuid.UUID,
    user: VerifiedUser,
    session: DbSession,
) -> MessageResponse:
    await _svc(session).delete(workspace_id, user)
    return MessageResponse(message="Workspace deleted.")


# ── Members ───────────────────────────────────────────────────────────────────

@router.get(
    "/{workspace_id}/members",
    response_model=list[MemberOut],
    summary="List workspace members",
)
async def list_members(
    workspace_id: uuid.UUID,
    user: VerifiedUser,
    session: DbSession,
) -> list[MemberOut]:
    return await _svc(session).list_members(workspace_id, user)


@router.post(
    "/{workspace_id}/members/invite",
    response_model=MemberOut,
    status_code=status.HTTP_201_CREATED,
    summary="Invite a user to the workspace by email (admin only)",
)
async def invite_member(
    workspace_id: uuid.UUID,
    data: InviteMemberRequest,
    user: VerifiedUser,
    session: DbSession,
) -> MemberOut:
    return await _svc(session).invite_member(workspace_id, data, user)


@router.post(
    "/invitations/accept",
    response_model=MemberOut,
    summary="Accept a workspace invitation",
)
async def accept_invitation(
    data: AcceptInviteRequest,
    user: VerifiedUser,
    session: DbSession,
) -> MemberOut:
    return await _svc(session).accept_invitation(data, user)


@router.patch(
    "/{workspace_id}/members/{target_user_id}/role",
    response_model=MemberOut,
    summary="Update a member's role (admin only)",
)
async def update_member_role(
    workspace_id: uuid.UUID,
    target_user_id: uuid.UUID,
    data: UpdateMemberRoleRequest,
    user: VerifiedUser,
    session: DbSession,
) -> MemberOut:
    return await _svc(session).update_member_role(workspace_id, target_user_id, data, user)


@router.delete(
    "/{workspace_id}/members/{target_user_id}",
    response_model=MessageResponse,
    summary="Remove a member from the workspace",
)
async def remove_member(
    workspace_id: uuid.UUID,
    target_user_id: uuid.UUID,
    user: VerifiedUser,
    session: DbSession,
) -> MessageResponse:
    await _svc(session).remove_member(workspace_id, target_user_id, user)
    return MessageResponse(message="Member removed.")