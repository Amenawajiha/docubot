"""
Chatbot endpoints — nested under /workspaces/{workspace_id}/chatbots.
"""

import uuid

from fastapi import APIRouter, Query, status

from app.api.dependencies import DbSession, VerifiedUser
from app.core.chatbot.service import ChatbotService
from app.schemas.auth import MessageResponse
from app.schemas.chatbot import (
    ChatbotCreate,
    ChatbotDeployResponse,
    ChatbotListOut,
    ChatbotOut,
    ChatbotUpdate,
)

router = APIRouter(
    prefix="/workspaces/{workspace_id}/chatbots",
    tags=["chatbots"],
)


def _svc(session: DbSession) -> ChatbotService:
    return ChatbotService(session)


@router.post(
    "",
    response_model=ChatbotOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new chatbot in a workspace",
)
async def create_chatbot(
    workspace_id: uuid.UUID,
    data: ChatbotCreate,
    user: VerifiedUser,
    session: DbSession,
) -> ChatbotOut:
    return await _svc(session).create(workspace_id, data, user)


@router.get(
    "",
    response_model=list[ChatbotListOut],
    summary="List chatbots in a workspace",
)
async def list_chatbots(
    workspace_id: uuid.UUID,
    user: VerifiedUser,
    session: DbSession,
    include_archived: bool = Query(default=False),
) -> list[ChatbotListOut]:
    return await _svc(session).list_for_workspace(
        workspace_id, user, include_archived=include_archived
    )


@router.get(
    "/{chatbot_id}",
    response_model=ChatbotOut,
    summary="Get chatbot details",
)
async def get_chatbot(
    workspace_id: uuid.UUID,
    chatbot_id: uuid.UUID,
    user: VerifiedUser,
    session: DbSession,
) -> ChatbotOut:
    return await _svc(session).get(workspace_id, chatbot_id, user)


@router.patch(
    "/{chatbot_id}",
    response_model=ChatbotOut,
    summary="Update chatbot configuration (editor+)",
)
async def update_chatbot(
    workspace_id: uuid.UUID,
    chatbot_id: uuid.UUID,
    data: ChatbotUpdate,
    user: VerifiedUser,
    session: DbSession,
) -> ChatbotOut:
    return await _svc(session).update(workspace_id, chatbot_id, data, user)


@router.delete(
    "/{chatbot_id}",
    response_model=MessageResponse,
    summary="Soft-delete (archive) a chatbot (admin+)",
)
async def delete_chatbot(
    workspace_id: uuid.UUID,
    chatbot_id: uuid.UUID,
    user: VerifiedUser,
    session: DbSession,
) -> MessageResponse:
    await _svc(session).delete(workspace_id, chatbot_id, user)
    return MessageResponse(message="Chatbot archived.")


@router.post(
    "/{chatbot_id}/deploy",
    response_model=ChatbotDeployResponse,
    summary="Publish chatbot (editor+) — returns embed snippet",
)
async def deploy_chatbot(
    workspace_id: uuid.UUID,
    chatbot_id: uuid.UUID,
    user: VerifiedUser,
    session: DbSession,
) -> ChatbotDeployResponse:
    return await _svc(session).deploy(workspace_id, chatbot_id, user)


@router.post(
    "/{chatbot_id}/pause",
    response_model=ChatbotOut,
    summary="Pause a published chatbot (editor+)",
)
async def pause_chatbot(
    workspace_id: uuid.UUID,
    chatbot_id: uuid.UUID,
    user: VerifiedUser,
    session: DbSession,
) -> ChatbotOut:
    return await _svc(session).pause(workspace_id, chatbot_id, user)