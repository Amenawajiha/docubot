"""
Knowledge base repositories — documents, jobs, chunks, collections.
All queries are scoped to (workspace_id, chatbot_id) for tenant isolation.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.models import (
    ChatbotCollection,
    ChatbotDocument,
    DocumentChunk,
    IngestionJob,
)
from app.data.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[ChatbotDocument]):
    model = ChatbotDocument

    async def get_by_id_for_chatbot(
        self,
        document_id: uuid.UUID,
        chatbot_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> ChatbotDocument | None:
        result = await self.session.execute(
            select(ChatbotDocument).where(
                ChatbotDocument.id == document_id,
                ChatbotDocument.chatbot_id == chatbot_id,
                ChatbotDocument.workspace_id == workspace_id,
                ChatbotDocument.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_for_chatbot(
        self,
        chatbot_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> list[ChatbotDocument]:
        result = await self.session.execute(
            select(ChatbotDocument)
            .where(
                ChatbotDocument.chatbot_id == chatbot_id,
                ChatbotDocument.workspace_id == workspace_id,
                ChatbotDocument.deleted_at.is_(None),
            )
            .order_by(ChatbotDocument.uploaded_at.desc())
        )
        return list(result.scalars().all())

    async def list_for_workspace(
        self,
        workspace_id: uuid.UUID,
    ) -> list[ChatbotDocument]:
        result = await self.session.execute(
            select(ChatbotDocument)
            .where(
                ChatbotDocument.workspace_id == workspace_id,
                ChatbotDocument.deleted_at.is_(None),
            )
            .order_by(ChatbotDocument.uploaded_at.desc())
        )
        return list(result.scalars().all())

    async def soft_delete(self, document: ChatbotDocument) -> ChatbotDocument:
        return await self.update(
            document,
            deleted_at=datetime.now(timezone.utc),
            upload_status="deleted",
        )

    async def mark_processing(self, document: ChatbotDocument) -> ChatbotDocument:
        return await self.update(document, upload_status="processing")

    async def mark_completed(
        self, document: ChatbotDocument, chunk_count: int
    ) -> ChatbotDocument:
        return await self.update(
            document,
            upload_status="completed",
            chunk_count=chunk_count,
            processed_at=datetime.now(timezone.utc),
        )

    async def mark_failed(
        self, document: ChatbotDocument, error: str
    ) -> ChatbotDocument:
        return await self.update(document, upload_status="failed", error_message=error)


class IngestionJobRepository(BaseRepository[IngestionJob]):
    model = IngestionJob

    async def get_by_id_for_chatbot(
        self,
        job_id: uuid.UUID,
        chatbot_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> IngestionJob | None:
        result = await self.session.execute(
            select(IngestionJob).where(
                IngestionJob.id == job_id,
                IngestionJob.chatbot_id == chatbot_id,
                IngestionJob.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_latest_for_document(
        self, document_id: uuid.UUID
    ) -> IngestionJob | None:
        result = await self.session.execute(
            select(IngestionJob)
            .where(IngestionJob.document_id == document_id)
            .order_by(IngestionJob.queued_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def update_status(
        self,
        job: IngestionJob,
        *,
        status: str,
        progress: int | None = None,
        chunks_created: int | None = None,
        error: str | None = None,
        celery_task_id: str | None = None,
    ) -> IngestionJob:
        updates: dict = {"job_status": status}
        if progress is not None:
            updates["progress_percent"] = progress
        if chunks_created is not None:
            updates["chunks_created"] = chunks_created
        if error is not None:
            updates["error_message"] = error
        if celery_task_id is not None:
            updates["celery_task_id"] = celery_task_id
        if status == "processing" and job.started_at is None:
            updates["started_at"] = datetime.now(timezone.utc)
        if status in ("completed", "failed"):
            updates["completed_at"] = datetime.now(timezone.utc)
        return await self.update(job, **updates)


class DocumentChunkRepository(BaseRepository[DocumentChunk]):
    model = DocumentChunk

    async def list_for_document(
        self, document_id: uuid.UUID
    ) -> list[DocumentChunk]:
        result = await self.session.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        )
        return list(result.scalars().all())

    async def get_qdrant_point_ids(
        self, document_id: uuid.UUID
    ) -> list[uuid.UUID]:
        """Return all Qdrant point IDs for a document (used during deletion)."""
        result = await self.session.execute(
            select(DocumentChunk.qdrant_point_id).where(
                DocumentChunk.document_id == document_id
            )
        )
        return [row[0] for row in result.all()]

    async def delete_for_document(self, document_id: uuid.UUID) -> int:
        """Hard-delete all chunks for a document. Returns count deleted."""
        chunks = await self.list_for_document(document_id)
        for chunk in chunks:
            await self.session.delete(chunk)
        await self.session.flush()
        return len(chunks)

    async def delete_for_chatbot(self, chatbot_id: uuid.UUID) -> int:
        """Hard-delete ALL chunks for a chatbot (used on KB clear)."""
        result = await self.session.execute(
            select(DocumentChunk).where(DocumentChunk.chatbot_id == chatbot_id)
        )
        chunks = list(result.scalars().all())
        for chunk in chunks:
            await self.session.delete(chunk)
        await self.session.flush()
        return len(chunks)


class CollectionRepository(BaseRepository[ChatbotCollection]):
    model = ChatbotCollection

    async def get_for_chatbot(
        self, chatbot_id: uuid.UUID
    ) -> ChatbotCollection | None:
        result = await self.session.execute(
            select(ChatbotCollection).where(
                ChatbotCollection.chatbot_id == chatbot_id
            )
        )
        return result.scalar_one_or_none()

    async def upsert_stats(
        self,
        workspace_id: uuid.UUID,
        chatbot_id: uuid.UUID,
        collection_name: str,
        total_documents: int,
        total_chunks: int,
        storage_used_bytes: int,
    ) -> ChatbotCollection:
        """Create or update the collection stats row."""
        existing = await self.get_for_chatbot(chatbot_id)
        now = datetime.now(timezone.utc)

        if existing:
            return await self.update(
                existing,
                total_documents=total_documents,
                total_chunks=total_chunks,
                storage_used_bytes=storage_used_bytes,
                last_synced_at=now,
                updated_at=now,
            )
        return await self.create(
            workspace_id=workspace_id,
            chatbot_id=chatbot_id,
            qdrant_collection_name=collection_name,
            total_documents=total_documents,
            total_chunks=total_chunks,
            storage_used_bytes=storage_used_bytes,
            last_synced_at=now,
        )