"""
Knowledge base endpoints — document upload, ingestion tracking, KB management.

All routes are nested under /workspaces/{workspace_id}/chatbots/{chatbot_id}.
"""

import uuid

from fastapi import APIRouter, File, UploadFile, status

from app.api.dependencies import DbSession, VerifiedUser
from app.core.knowledge.service import KnowledgeService
from app.schemas.auth import MessageResponse
from app.schemas.knowledge import (
    ClearResponse,
    DocumentOut,
    IngestionJobOut,
    KnowledgeBaseStats,
    SyncResponse,
    UploadResponse,
)

router = APIRouter(
    prefix="/workspaces/{workspace_id}/chatbots/{chatbot_id}",
    tags=["knowledge base"],
)


def _svc(session: DbSession) -> KnowledgeService:
    return KnowledgeService(session)


# ── Upload ────────────────────────────────────────────────────────────────────

@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a document to the chatbot knowledge base",
    description=(
        "Accepts a file upload (PDF, DOCX, XLSX, TXT, MD, CSV, images). "
        "Saves to S3, queues a Celery ingestion task in chatbot-rag, and "
        "returns document_id + job_id for status polling."
    ),
)
async def upload_document(
    workspace_id: uuid.UUID,
    chatbot_id: uuid.UUID,
    user: VerifiedUser,
    session: DbSession,
    file: UploadFile = File(...),
) -> UploadResponse:
    file_bytes = await file.read()
    return await _svc(session).upload_document(
        workspace_id=workspace_id,
        chatbot_id=chatbot_id,
        actor=user,
        filename=file.filename or "upload",
        file_bytes=file_bytes,
    )


# ── Ingestion job polling ─────────────────────────────────────────────────────

@router.get(
    "/ingestion-jobs/{job_id}",
    response_model=IngestionJobOut,
    summary="Poll ingestion job status",
    description=(
        "Poll this endpoint after upload until job_status is 'completed' or 'failed'. "
        "Typical polling interval: every 2 seconds."
    ),
)
async def get_ingestion_job(
    workspace_id: uuid.UUID,
    chatbot_id: uuid.UUID,
    job_id: uuid.UUID,
    user: VerifiedUser,
    session: DbSession,
) -> IngestionJobOut:
    return await _svc(session).get_job_status(
        workspace_id, chatbot_id, job_id, user
    )


# ── Documents ─────────────────────────────────────────────────────────────────

@router.get(
    "/documents",
    response_model=list[DocumentOut],
    summary="List all documents in the chatbot knowledge base",
)
async def list_documents(
    workspace_id: uuid.UUID,
    chatbot_id: uuid.UUID,
    user: VerifiedUser,
    session: DbSession,
) -> list[DocumentOut]:
    return await _svc(session).list_documents(workspace_id, chatbot_id, user)


@router.delete(
    "/documents/{document_id}",
    response_model=MessageResponse,
    summary="Delete a document and its vectors (editor+)",
    description=(
        "Soft-deletes the document record, dispatches a Celery task to "
        "remove its vectors from Qdrant, and deletes the file from S3."
    ),
)
async def delete_document(
    workspace_id: uuid.UUID,
    chatbot_id: uuid.UUID,
    document_id: uuid.UUID,
    user: VerifiedUser,
    session: DbSession,
) -> MessageResponse:
    await _svc(session).delete_document(
        workspace_id, chatbot_id, document_id, user
    )
    return MessageResponse(message="Document deleted and vectors queued for removal.")


# ── Knowledge base management ─────────────────────────────────────────────────

@router.get(
    "/knowledge-base/stats",
    response_model=KnowledgeBaseStats,
    summary="Get knowledge base statistics",
    description="Returns document count, chunk count, storage size, and last sync time.",
)
async def get_kb_stats(
    workspace_id: uuid.UUID,
    chatbot_id: uuid.UUID,
    user: VerifiedUser,
    session: DbSession,
) -> KnowledgeBaseStats:
    return await _svc(session).get_kb_stats(workspace_id, chatbot_id, user)


@router.post(
    "/knowledge-base/sync",
    response_model=SyncResponse,
    summary="Force-rebuild the Qdrant collection (editor+)",
    description=(
        "Dispatches a Celery task to rebuild the collection from all completed "
        "documents. Returns immediately — the actual sync happens asynchronously."
    ),
)
async def sync_knowledge_base(
    workspace_id: uuid.UUID,
    chatbot_id: uuid.UUID,
    user: VerifiedUser,
    session: DbSession,
) -> SyncResponse:
    return await _svc(session).sync_knowledge_base(workspace_id, chatbot_id, user)


@router.delete(
    "/knowledge-base/clear",
    response_model=ClearResponse,
    summary="Clear ALL documents and vectors (admin+)",
    description=(
        "Destructive: removes all documents, chunks, and Qdrant vectors "
        "for this chatbot. Requires admin role."
    ),
)
async def clear_knowledge_base(
    workspace_id: uuid.UUID,
    chatbot_id: uuid.UUID,
    user: VerifiedUser,
    session: DbSession,
) -> ClearResponse:
    return await _svc(session).clear_knowledge_base(workspace_id, chatbot_id, user)