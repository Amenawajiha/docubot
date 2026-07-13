"""
Internal API endpoints — chatbot-rag ↔ website backend.

All routes require X-Internal-API-Key header.
These endpoints are NOT accessible to end-users or workspace members.

Routes:
  GET  /internal/chatbot-config/{workspace_id}/{chatbot_id}   ← chatbot-rag fetches config
  POST /internal/ingestion-jobs/{job_id}                      ← chatbot-rag posts job status
  POST /internal/usage/tokens                                 ← chatbot-rag logs token use
  POST /internal/workspace/{workspace_id}/check-quota        ← chatbot-rag checks quota

Admin-only (workspace member JWT, not internal key):
  POST /internal/keys                                         ← create internal API key
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Security, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import DbSession, VerifiedUser
from app.core.internal.service import InternalService
from app.data.database import get_db
from app.schemas.chat import (
    ChatbotConfigInternal,
    CreateInternalKeyRequest,
    IngestionCallbackRequest,
    InternalKeyOut,
    QuotaCheckRequest,
    QuotaCheckResponse,
    TokenUsageRequest,
)
from app.utils.exceptions import UnauthorizedError

router = APIRouter(prefix="/internal", tags=["internal"])


# ── Internal key dependency ───────────────────────────────────────────────────

async def require_internal_key(
    x_internal_api_key: Annotated[str | None, Header()] = None,
    session: AsyncSession = Depends(get_db),
) -> None:
    """
    FastAPI dependency that validates the X-Internal-API-Key header.
    Raises 401 if the key is missing or invalid.
    """
    if not x_internal_api_key:
        raise UnauthorizedError("X-Internal-API-Key header is required.")
    svc = InternalService(session)
    await svc.verify_internal_key(x_internal_api_key)


InternalAuth = Annotated[None, Depends(require_internal_key)]


# ── Config endpoint ───────────────────────────────────────────────────────────

@router.get(
    "/chatbot-config/{workspace_id}/{chatbot_id}",
    response_model=ChatbotConfigInternal,
    summary="Get full chatbot config including decrypted API key",
    description=(
        "Called by chatbot-rag to load per-chatbot config. "
        "Returns the decrypted LLM API key — internal auth required."
    ),
)
async def get_chatbot_config(
    workspace_id: uuid.UUID,
    chatbot_id: uuid.UUID,
    _auth: InternalAuth,
    session: DbSession,
) -> ChatbotConfigInternal:
    return await InternalService(session).get_chatbot_config(
        workspace_id, chatbot_id
    )


# ── Ingestion callback ────────────────────────────────────────────────────────

@router.post(
    "/ingestion-jobs/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Ingestion job status callback from chatbot-rag",
    description=(
        "chatbot-rag posts here when a Celery ingestion task changes state. "
        "Updates ingestion_jobs and chatbot_documents in the website DB."
    ),
)
async def ingestion_callback(
    job_id: uuid.UUID,
    data: IngestionCallbackRequest,
    _auth: InternalAuth,
    session: DbSession,
) -> None:
    await InternalService(session).handle_ingestion_callback(job_id, data)


# ── Token usage logging ───────────────────────────────────────────────────────

@router.post(
    "/usage/tokens",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Log token consumption after a chat response",
    description="chatbot-rag calls this after every LLM response to record usage.",
)
async def log_token_usage(
    data: TokenUsageRequest,
    _auth: InternalAuth,
    session: DbSession,
) -> None:
    await InternalService(session).log_token_usage(data)


# ── Quota check ───────────────────────────────────────────────────────────────

@router.post(
    "/workspace/{workspace_id}/check-quota",
    response_model=QuotaCheckResponse,
    summary="Check if a workspace can make another request",
    description=(
        "chatbot-rag calls this before processing a chat message. "
        "Returns { allowed, remaining_tokens, reason }."
    ),
)
async def check_quota(
    workspace_id: uuid.UUID,
    data: QuotaCheckRequest,
    _auth: InternalAuth,
    session: DbSession,
) -> QuotaCheckResponse:
    return await InternalService(session).check_quota(workspace_id, data)


# ── Key management ────────────────────────────────────────────────────────────

@router.post(
    "/keys",
    response_model=InternalKeyOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create an internal API key (superadmin only)",
    description=(
        "Creates a new shared secret for backend-to-backend auth. "
        "The raw key is returned ONCE and cannot be retrieved again."
    ),
)
async def create_internal_key(
    data: CreateInternalKeyRequest,
    user: VerifiedUser,
    session: DbSession,
) -> InternalKeyOut:
    if user.email != "superadmin@docubot.app":
        from app.utils.exceptions import ForbiddenError
        raise ForbiddenError("Superadmin only.")
    
    # TODO: restrict to superadmin role once that concept exists
    return await InternalService(session).create_internal_key(data)