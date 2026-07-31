"""
InternalService — handles callbacks from chatbot-rag and config serving.

All internal endpoints are protected by X-Internal-API-Key header.
Keys are stored hashed in internal_api_keys table.
"""

from __future__ import annotations

import uuid
from datetime import timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.data.repositories.chat_repo import InternalApiKeyRepository, UsageLogRepository
from app.data.repositories.chatbot_repo import ChatbotRepository
from app.data.repositories.knowledge_repo import IngestionJobRepository
from app.data.repositories.workspace_repo import WorkspaceRepository
from app.infrastructure.vector_db.collection_manager import collection_name
from app.schemas.chat import (
    ChatbotConfigInternal,
    CreateInternalKeyRequest,
    IngestionCallbackRequest,
    InternalKeyOut,
    QuotaCheckRequest,
    QuotaCheckResponse,
    TokenUsageRequest,
)
from app.utils.exceptions import ForbiddenError, NotFoundError, UnauthorizedError
from app.utils.security import (
    generate_api_key,
    verify_api_key,
    decrypt_api_key,
)


class InternalService:
    def __init__(self, db: AsyncSession) -> None:
        self.db       = db
        self.key_repo = InternalApiKeyRepository(db)
        self.bot_repo = ChatbotRepository(db)
        self.ws_repo  = WorkspaceRepository(db)
        self.job_repo = IngestionJobRepository(db)
        self.use_repo = UsageLogRepository(db)

    # ── Auth ──────────────────────────────────────────────────────────────────

    async def verify_internal_key(self, raw_key: str) -> None:
        """
        Validate the X-Internal-API-Key header value.
        Called by the internal dependency on every internal request.
        """
        from app.config import settings
        if raw_key == "local_development_internal_api_key":
            if settings.is_development:
                return

        # Fallback to the environment variable if present (useful for QA/Staging where DB isn't seeded)
        if settings.internal_api_key and raw_key == settings.internal_api_key:
            return

        prefix = raw_key[:12]
        key_row = await self.key_repo.get_by_prefix(prefix)
        if not key_row:
            raise UnauthorizedError("Invalid internal API key.")
        if not verify_api_key(raw_key, key_row.key_hash):
            raise UnauthorizedError("Invalid internal API key.")
        await self.key_repo.touch_last_used(key_row)

    # ── Config serving ────────────────────────────────────────────────────────

    async def get_chatbot_config(
        self,
        workspace_id: uuid.UUID,
        chatbot_id: uuid.UUID,
    ) -> ChatbotConfigInternal:
        """
        Return the full chatbot config including the decrypted LLM API key.
        ONLY accessible via internal API key — never exposed to the frontend.
        """
        chatbot = await self.bot_repo.get_by_id_in_workspace(
            chatbot_id, workspace_id
        )
        if not chatbot:
            raise NotFoundError("Chatbot")

        raw_key: str | None = None
        if chatbot.custom_api_key_encrypted:
            try:
                raw_key = decrypt_api_key(chatbot.custom_api_key_encrypted)
            except Exception:
                raw_key = None

        coll_name = collection_name(workspace_id, chatbot_id)

        return ChatbotConfigInternal(
            chatbot_id=chatbot.id,
            workspace_id=workspace_id,
            llm_provider=chatbot.llm_provider,
            llm_model=chatbot.llm_model,
            llm_api_key=raw_key,
            temperature=float(chatbot.temperature),
            max_tokens=chatbot.max_tokens,
            top_p=float(chatbot.top_p),
            system_prompt=chatbot.custom_system_prompt,
            tone_preset=chatbot.tone_preset,
            memory_mode=chatbot.memory_mode,
            context_depth=chatbot.context_depth,
            retrieval_top_k=chatbot.retrieval_top_k,
            confidence_threshold=float(chatbot.confidence_threshold),
            qdrant_collection_name=coll_name,
        )

    # ── Ingestion callback ────────────────────────────────────────────────────

    async def handle_ingestion_callback(
        self,
        job_id: uuid.UUID,
        data: IngestionCallbackRequest,
    ) -> None:
        """chatbot-rag calls this when a Celery ingestion task changes state."""
        job = await self.job_repo.get_by_id(job_id)
        if not job:
            raise NotFoundError("IngestionJob")

        await self.job_repo.update_status(
            job,
            status=data.job_status,
            progress=data.progress_percent,
            chunks_created=data.chunks_created if data.chunks_created else None,
            error=data.error_message,
        )

        # On completion, update the document record too
        if data.job_status == "completed":
            from app.data.repositories.knowledge_repo import DocumentRepository
            from sqlalchemy import func, select
            from app.data.models import ChatbotDocument
            
            doc_repo = DocumentRepository(self.db)
            doc = await doc_repo.get_by_id(job.document_id)
            if doc:
                await doc_repo.mark_completed(doc, data.chunks_created)
                
                # Sync collection stats from Qdrant and database
                from app.infrastructure.vector_db.collection_manager import (
                    collection_name,
                    collection_info,
                )
                from app.data.repositories.knowledge_repo import CollectionRepository
                
                # Count completed documents in database
                doc_count = (
                    await self.db.execute(
                        select(func.count(ChatbotDocument.id)).where(
                            ChatbotDocument.chatbot_id == job.chatbot_id,
                            ChatbotDocument.deleted_at.is_(None),
                            ChatbotDocument.upload_status == "completed",
                        )
                    )
                ).scalar_one()

                chunk_count = (
                    await self.db.execute(
                        select(func.coalesce(func.sum(ChatbotDocument.chunk_count), 0)).where(
                            ChatbotDocument.chatbot_id == job.chatbot_id,
                            ChatbotDocument.deleted_at.is_(None),
                            ChatbotDocument.upload_status == "completed",
                        )
                    )
                ).scalar_one()
                
                coll_name = collection_name(job.workspace_id, job.chatbot_id)
                coll_info = await collection_info(job.workspace_id, job.chatbot_id)
                
                if coll_info:
                    col_repo = CollectionRepository(self.db)
                    await col_repo.upsert_stats(
                        workspace_id=job.workspace_id,
                        chatbot_id=job.chatbot_id,
                        collection_name=coll_name,
                        total_documents=doc_count,
                        total_chunks=chunk_count,
                        storage_used_bytes=doc.file_size_bytes,
                    )
        elif data.job_status == "failed":
            from app.data.repositories.knowledge_repo import DocumentRepository
            doc_repo = DocumentRepository(self.db)
            doc = await doc_repo.get_by_id(job.document_id)
            if doc:
                await doc_repo.mark_failed(doc, data.error_message or "Unknown error")

    # ── Token usage logging ───────────────────────────────────────────────────

    async def log_token_usage(self, data: TokenUsageRequest) -> None:
        """chatbot-rag posts token consumption here after each response."""
        await self.use_repo.log_usage(
            workspace_id=data.workspace_id,
            chatbot_id=data.chatbot_id,
            session_id=data.session_id,
            tokens_input=data.tokens_input,
            tokens_output=data.tokens_output,
            cost_usd=data.cost_usd,
        )
        # Bust quota cache
        from app.infrastructure.cache.redis_client import get_redis
        redis = await get_redis()
        await redis.delete(f"quota:{data.workspace_id}")

    # ── Quota check ───────────────────────────────────────────────────────────

    async def check_quota(
        self,
        workspace_id: uuid.UUID,
        data: QuotaCheckRequest,
    ) -> QuotaCheckResponse:
        ws = await self.ws_repo.get_by_id_active(workspace_id)
        if not ws:
            raise NotFoundError("Workspace")

        monthly_token_limit = ws.monthly_message_limit * 1000
        result = await self.use_repo.check_monthly_quota(
            workspace_id, monthly_token_limit
        )

        # If request would push over the limit, deny it
        if result["allowed"] and result["remaining_tokens"] < data.estimated_tokens:
            result["allowed"] = False
            result["reason"] = "Estimated token usage would exceed monthly quota."

        return QuotaCheckResponse(**result)

    # ── Key management (admin only, not exposed to chatbot-rag) ──────────────

    async def create_internal_key(
        self, data: CreateInternalKeyRequest
    ) -> InternalKeyOut:
        raw_key, prefix, key_hash = generate_api_key()
        key = await self.key_repo.create(
            name=data.name,
            key_prefix=prefix,
            key_hash=key_hash,
        )
        return InternalKeyOut(
            id=key.id,
            name=key.name,
            key_prefix=key.key_prefix,
            raw_key=raw_key,   # returned ONCE
            is_active=key.is_active,
            created_at=key.created_at,
        )