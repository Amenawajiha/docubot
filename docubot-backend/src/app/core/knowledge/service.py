"""
KnowledgeService — document upload, ingestion tracking, KB management.

Responsibilities
----------------
1. Accept file uploads → save to S3 → create DB records → dispatch Celery task
2. Poll ingestion job status (frontend polls this while processing)
3. List / delete documents (soft-delete DB + hard-delete Qdrant points + S3)
4. Return knowledge base stats (from chatbot_collections cache)
5. Force-sync (rebuild) or clear the entire collection

The split is deliberate: this backend manages metadata and orchestrates;
chatbot-rag does the heavy CPU/IO work asynchronously.
"""

from __future__ import annotations

import time
import uuid
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.data.models import Chatbot, User
from app.data.repositories.chatbot_repo import ChatbotRepository
from app.data.repositories.knowledge_repo import (
    CollectionRepository,
    DocumentChunkRepository,
    DocumentRepository,
    IngestionJobRepository,
)
from app.data.repositories.workspace_repo import (
    WorkspaceMemberRepository,
    WorkspaceRepository,
)
from app.infrastructure.queue.celery_app import (
    TASK_CLEAR_COLLECTION,
    TASK_DELETE_DOCUMENT,
    TASK_INGEST_DOCUMENT,
    TASK_SYNC_COLLECTION,
    celery_app,
)
from app.infrastructure.storage.s3_client import (
    build_storage_key,
    delete_file,
    generate_presigned_url,
    upload_file,
)
from app.infrastructure.vector_db.collection_manager import (
    collection_name,
    delete_collection,
    delete_points_for_document,
    ensure_collection,
)
from app.schemas.knowledge import (
    ClearResponse,
    DocumentOut,
    IngestionJobOut,
    KnowledgeBaseStats,
    SyncResponse,
    UploadResponse,
)
from app.utils.exceptions import BadRequestError, ForbiddenError, NotFoundError

# Permitted file extensions → MIME type mapping
_ALLOWED_EXTENSIONS: dict[str, str] = {
    ".pdf":  "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".doc":  "application/msword",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls":  "application/vnd.ms-excel",
    ".txt":  "text/plain",
    ".md":   "text/markdown",
    ".csv":  "text/csv",
    ".png":  "image/png",
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}

_MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024   # 50 MB

_ROLE_RANK = {"viewer": 0, "editor": 1, "admin": 2}


class KnowledgeService:
    def __init__(self, session: AsyncSession) -> None:
        self.session       = session
        self.doc_repo      = DocumentRepository(session)
        self.job_repo      = IngestionJobRepository(session)
        self.chunk_repo    = DocumentChunkRepository(session)
        self.col_repo      = CollectionRepository(session)
        self.bot_repo      = ChatbotRepository(session)
        self.ws_repo       = WorkspaceRepository(session)
        self.mem_repo      = WorkspaceMemberRepository(session)

    # ── Upload ────────────────────────────────────────────────────────────────

    async def upload_document(
        self,
        workspace_id: uuid.UUID,
        chatbot_id: uuid.UUID,
        actor: User,
        filename: str,
        file_bytes: bytes,
    ) -> UploadResponse:
        """
        Full upload pipeline:
          1. Validate membership + role
          2. Validate file type + size
          3. Create chatbot_documents row (status=pending)
          4. Upload file to S3
          5. Ensure Qdrant collection exists
          6. Create ingestion_jobs row (status=queued)
          7. Dispatch Celery task to chatbot-rag worker
          8. Return {document_id, job_id}
        """
        chatbot = await self._require_chatbot(workspace_id, chatbot_id)
        await self._require_role(workspace_id, actor.id, "editor")

        # Validate file
        suffix      = Path(filename).suffix.lower()
        content_type = _ALLOWED_EXTENSIONS.get(suffix)
        if not content_type:
            raise BadRequestError(
                f"File type '{suffix}' is not supported. "
                f"Allowed: {', '.join(_ALLOWED_EXTENSIONS)}"
            )
        if len(file_bytes) > _MAX_FILE_SIZE_BYTES:
            raise BadRequestError(
                f"File exceeds the 50 MB size limit "
                f"({len(file_bytes) / 1_048_576:.1f} MB)."
            )
        if len(file_bytes) == 0:
            raise BadRequestError("File is empty.")

        # Create document record
        document_id = uuid.uuid4()
        document = await self.doc_repo.create(
            id=document_id,
            workspace_id=workspace_id,
            chatbot_id=chatbot_id,
            filename=filename,
            original_filename=filename,
            file_type=suffix.lstrip("."),
            file_size_bytes=len(file_bytes),
            upload_status="pending",
        )

        # Upload to S3
        storage_key = build_storage_key(workspace_id, chatbot_id, document_id, filename)
        await upload_file(storage_key, file_bytes, content_type)
        await self.doc_repo.update(document, storage_key=storage_key, upload_status="uploaded")

        # Ensure Qdrant collection exists (idempotent)
        coll_name = await ensure_collection(workspace_id, chatbot_id)

        # Ensure collection registry row exists
        await self.col_repo.upsert_stats(
            workspace_id=workspace_id,
            chatbot_id=chatbot_id,
            collection_name=coll_name,
            total_documents=0,
            total_chunks=0,
            storage_used_bytes=0,
        )

        # Create ingestion job record
        job_id = uuid.uuid4()
        job = await self.job_repo.create(
            id=job_id,
            workspace_id=workspace_id,
            chatbot_id=chatbot_id,
            document_id=document_id,
            job_status="queued",
        )

        # Generate a presigned URL so the worker can download the file
        download_url = await generate_presigned_url(storage_key, expires_in=7200)

        # Dispatch to chatbot-rag Celery worker
        # The worker receives enough context to load its own chatbot config
        task = celery_app.send_task(
            TASK_INGEST_DOCUMENT,
            kwargs={
                "job_id":          str(job_id),
                "document_id":     str(document_id),
                "workspace_id":    str(workspace_id),
                "chatbot_id":      str(chatbot_id),
                "filename":        filename,
                "file_type":       suffix.lstrip("."),
                "download_url":    download_url,
                "collection_name": coll_name,
            },
        )

        # Store Celery task ID for status polling
        await self.job_repo.update_status(
            job, status="queued", celery_task_id=task.id
        )

        return UploadResponse(
            document_id=document_id,
            job_id=job_id,
            filename=filename,
            file_type=suffix.lstrip("."),
            file_size_bytes=len(file_bytes),
            upload_status="uploaded",
            message="Document uploaded. Ingestion has been queued.",
        )

    # ── Job status polling ────────────────────────────────────────────────────

    async def get_job_status(
        self,
        workspace_id: uuid.UUID,
        chatbot_id: uuid.UUID,
        job_id: uuid.UUID,
        actor: User,
    ) -> IngestionJobOut:
        await self._require_member(workspace_id, actor.id)
        job = await self.job_repo.get_by_id_for_chatbot(
            job_id, chatbot_id, workspace_id
        )
        if not job:
            raise NotFoundError("IngestionJob")
        return IngestionJobOut.model_validate(job)

    # ── Document list ─────────────────────────────────────────────────────────

    async def list_documents(
        self,
        workspace_id: uuid.UUID,
        chatbot_id: uuid.UUID,
        actor: User,
    ) -> list[DocumentOut]:
        await self._require_chatbot(workspace_id, chatbot_id)
        await self._require_member(workspace_id, actor.id)
        docs = await self.doc_repo.list_for_chatbot(chatbot_id, workspace_id)
        return [DocumentOut.model_validate(d) for d in docs]

    async def list_documents_for_workspace(
        self,
        workspace_id: uuid.UUID,
        actor: User,
    ) -> list[DocumentOut]:
        await self._require_member(workspace_id, actor.id)
        docs = await self.doc_repo.list_for_workspace(workspace_id)
        return [DocumentOut.model_validate(d) for d in docs]

    # ── Document delete ───────────────────────────────────────────────────────

    async def delete_document(
        self,
        workspace_id: uuid.UUID,
        chatbot_id: uuid.UUID,
        document_id: uuid.UUID,
        actor: User,
    ) -> None:
        """
        Remove a document:
          1. Soft-delete the DB record
          2. Delete Qdrant vectors for its chunks
          3. Hard-delete chunks from DB
          4. Delete file from S3
          5. Refresh collection stats
        """
        await self._require_role(workspace_id, actor.id, "editor")
        document = await self.doc_repo.get_by_id_for_chatbot(
            document_id, chatbot_id, workspace_id
        )
        if not document:
            raise NotFoundError("Document")

        # Soft-delete the document row
        await self.doc_repo.soft_delete(document)

        # Dispatch async deletion of Qdrant points by filename
        celery_app.send_task(
            TASK_DELETE_DOCUMENT,
            kwargs={
                "workspace_id":    str(workspace_id),
                "chatbot_id":      str(chatbot_id),
                "document_id":     str(document_id),
                "filename":        document.filename,
                "collection_name": collection_name(workspace_id, chatbot_id),
            },
        )

        # Delete from S3
        if document.storage_key:
            try:
                await delete_file(document.storage_key)
            except Exception:
                pass  # Log but don't fail — S3 cleanup is best-effort

        # Refresh collection stats
        await self._refresh_collection_stats(workspace_id, chatbot_id)

    # ── KB stats ──────────────────────────────────────────────────────────────

    async def get_kb_stats(
        self,
        workspace_id: uuid.UUID,
        chatbot_id: uuid.UUID,
        actor: User,
    ) -> KnowledgeBaseStats:
        await self._require_chatbot(workspace_id, chatbot_id)
        await self._require_member(workspace_id, actor.id)

        col = await self.col_repo.get_for_chatbot(chatbot_id)
        if not col:
            # Collection not yet created — return zeroes
            coll_name = collection_name(workspace_id, chatbot_id)
            return KnowledgeBaseStats(
                chatbot_id=chatbot_id,
                workspace_id=workspace_id,
                qdrant_collection_name=coll_name,
                total_documents=0,
                total_chunks=0,
                storage_used_mb=0.0,
                last_synced_at=None,
            )

        return KnowledgeBaseStats(
            chatbot_id=chatbot_id,
            workspace_id=workspace_id,
            qdrant_collection_name=col.qdrant_collection_name,
            total_documents=col.total_documents,
            total_chunks=col.total_chunks,
            storage_used_mb=round(col.storage_used_bytes / 1_048_576, 2),
            last_synced_at=col.last_synced_at,
        )

    # ── Force sync ────────────────────────────────────────────────────────────

    async def sync_knowledge_base(
        self,
        workspace_id: uuid.UUID,
        chatbot_id: uuid.UUID,
        actor: User,
    ) -> SyncResponse:
        """
        Force-rebuild the Qdrant collection from all completed documents.
        Dispatches a Celery task and returns immediately with the job result
        from the last sync (actual new data arrives via polling).
        """
        await self._require_chatbot(workspace_id, chatbot_id)
        await self._require_role(workspace_id, actor.id, "editor")

        coll_name = collection_name(workspace_id, chatbot_id)
        start_ms  = int(time.time() * 1000)

        # Get completed document IDs to pass to the worker
        docs = await self.doc_repo.list_for_chatbot(chatbot_id, workspace_id)
        completed_ids = [
            str(d.id) for d in docs if d.upload_status == "completed"
        ]

        task = celery_app.send_task(
            TASK_SYNC_COLLECTION,
            kwargs={
                "workspace_id":    str(workspace_id),
                "chatbot_id":      str(chatbot_id),
                "collection_name": coll_name,
                "document_ids":    completed_ids,
            },
        )

        elapsed = int(time.time() * 1000) - start_ms

        col = await self.col_repo.get_for_chatbot(chatbot_id)
        return SyncResponse(
            status="sync_queued",
            chunks_synced=col.total_chunks if col else 0,
            documents_processed=len(completed_ids),
            time_taken_ms=elapsed,
        )

    # ── Clear knowledge base ──────────────────────────────────────────────────

    async def clear_knowledge_base(
        self,
        workspace_id: uuid.UUID,
        chatbot_id: uuid.UUID,
        actor: User,
    ) -> ClearResponse:
        """
        Delete ALL documents and empty the Qdrant collection.
        Requires admin+ role (destructive operation).
        """
        await self._require_chatbot(workspace_id, chatbot_id)
        await self._require_role(workspace_id, actor.id, "admin")

        # Count before deletion for the response
        docs   = await self.doc_repo.list_for_chatbot(chatbot_id, workspace_id)
        chunks = await self.chunk_repo.delete_for_chatbot(chatbot_id)

        doc_count = len(docs)
        for doc in docs:
            await self.doc_repo.soft_delete(doc)
            if doc.storage_key:
                try:
                    await delete_file(doc.storage_key)
                except Exception:
                    pass

        # Dispatch Qdrant collection clear to worker (or do it directly)
        celery_app.send_task(
            TASK_CLEAR_COLLECTION,
            kwargs={
                "workspace_id":    str(workspace_id),
                "chatbot_id":      str(chatbot_id),
                "collection_name": collection_name(workspace_id, chatbot_id),
            },
        )

        # Reset stats cache
        col = await self.col_repo.get_for_chatbot(chatbot_id)
        if col:
            await self.col_repo.upsert_stats(
                workspace_id=workspace_id,
                chatbot_id=chatbot_id,
                collection_name=col.qdrant_collection_name,
                total_documents=0,
                total_chunks=0,
                storage_used_bytes=0,
            )

        return ClearResponse(
            status="cleared",
            documents_deleted=doc_count,
            chunks_deleted=chunks,
            message="All documents and vectors have been removed.",
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _require_chatbot(
        self, workspace_id: uuid.UUID, chatbot_id: uuid.UUID
    ) -> Chatbot:
        bot = await self.bot_repo.get_by_id_in_workspace(chatbot_id, workspace_id)
        if not bot:
            raise NotFoundError("Chatbot")
        return bot

    async def _require_member(
        self, workspace_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        member = await self.mem_repo.get_membership(workspace_id, user_id)
        if not member or member.joined_at is None:
            raise ForbiddenError("You are not a member of this workspace.")

    async def _require_role(
        self, workspace_id: uuid.UUID, user_id: uuid.UUID, min_role: str
    ) -> None:
        ws = await self.ws_repo.get_by_id_active(workspace_id)
        if ws and ws.owner_id == user_id:
            return   # owner always passes
        member = await self.mem_repo.get_membership(workspace_id, user_id)
        if not member or member.joined_at is None:
            raise ForbiddenError("You are not a member of this workspace.")
        if _ROLE_RANK.get(member.role, -1) < _ROLE_RANK.get(min_role, 99):
            raise ForbiddenError(
                f"This action requires at least the '{min_role}' role."
            )

    async def _refresh_collection_stats(
        self, workspace_id: uuid.UUID, chatbot_id: uuid.UUID
    ) -> None:
        """Recount from DB and update the chatbot_collections cache row."""
        from sqlalchemy import func, select
        from app.data.models import ChatbotDocument, DocumentChunk

        doc_count = (
            await self.session.execute(
                select(func.count(ChatbotDocument.id)).where(
                    ChatbotDocument.chatbot_id == chatbot_id,
                    ChatbotDocument.deleted_at.is_(None),
                    ChatbotDocument.upload_status == "completed",
                )
            )
        ).scalar_one()

        chunk_count = (
            await self.session.execute(
                select(func.count(DocumentChunk.id)).where(
                    DocumentChunk.chatbot_id == chatbot_id
                )
            )
        ).scalar_one()

        size_bytes = (
            await self.session.execute(
                select(func.coalesce(func.sum(ChatbotDocument.file_size_bytes), 0)).where(
                    ChatbotDocument.chatbot_id == chatbot_id,
                    ChatbotDocument.deleted_at.is_(None),
                )
            )
        ).scalar_one()

        coll_name = collection_name(workspace_id, chatbot_id)
        await self.col_repo.upsert_stats(
            workspace_id=workspace_id,
            chatbot_id=chatbot_id,
            collection_name=coll_name,
            total_documents=doc_count,
            total_chunks=chunk_count,
            storage_used_bytes=int(size_bytes),
        )