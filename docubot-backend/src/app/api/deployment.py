"""Deployment channel endpoints — Phase 7."""

import uuid

from fastapi import APIRouter, status

from app.api.dependencies import DbSession, VerifiedUser
from app.core.deployment.service import DeploymentService
from app.schemas.auth import MessageResponse
from app.schemas.deployment import (
    ChannelOut,
    CreateChannelRequest,
    UpdateChannelRequest,
    WidgetEmbedOut,
)

router = APIRouter(
    prefix="/workspaces/{workspace_id}/chatbots/{chatbot_id}/channels",
    tags=["deployment"],
)


def _svc(session: DbSession) -> DeploymentService:
    return DeploymentService(session)


@router.get("", response_model=list[ChannelOut], summary="List deployment channels")
async def list_channels(
    workspace_id: uuid.UUID,
    chatbot_id: uuid.UUID,
    user: VerifiedUser,
    session: DbSession,
) -> list[ChannelOut]:
    return await _svc(session).list_channels(workspace_id, chatbot_id, user.id)


@router.post(
    "",
    response_model=ChannelOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a deployment channel (editor+)",
)
async def create_channel(
    workspace_id: uuid.UUID,
    chatbot_id: uuid.UUID,
    data: CreateChannelRequest,
    user: VerifiedUser,
    session: DbSession,
) -> ChannelOut:
    return await _svc(session).create_channel(
        workspace_id, chatbot_id, data, user.id
    )


@router.patch(
    "/{channel_id}",
    response_model=ChannelOut,
    summary="Update a deployment channel",
)
async def update_channel(
    workspace_id: uuid.UUID,
    chatbot_id: uuid.UUID,
    channel_id: uuid.UUID,
    data: UpdateChannelRequest,
    user: VerifiedUser,
    session: DbSession,
) -> ChannelOut:
    return await _svc(session).update_channel(
        workspace_id, chatbot_id, channel_id, data, user.id
    )


@router.delete(
    "/{channel_id}",
    response_model=MessageResponse,
    summary="Delete a deployment channel (admin+)",
)
async def delete_channel(
    workspace_id: uuid.UUID,
    chatbot_id: uuid.UUID,
    channel_id: uuid.UUID,
    user: VerifiedUser,
    session: DbSession,
) -> MessageResponse:
    await _svc(session).delete_channel(
        workspace_id, chatbot_id, channel_id, user.id
    )
    return MessageResponse(message="Channel deleted.")


@router.get(
    "/{channel_id}/embed",
    response_model=WidgetEmbedOut,
    summary="Get widget embed snippet",
)
async def get_embed_snippet(
    workspace_id: uuid.UUID,
    chatbot_id: uuid.UUID,
    channel_id: uuid.UUID,
    user: VerifiedUser,
    session: DbSession,
) -> WidgetEmbedOut:
    return await _svc(session).get_embed_snippet(
        workspace_id, chatbot_id, channel_id, user.id
    )