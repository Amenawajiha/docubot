"""
Pydantic schemas for Phase 3 — knowledge base management.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ── Upload ────────────────────────────────────────────────────────────────────

class UploadResponse(BaseModel):
    document_id: uuid.UUID
    job_id: uuid.UUID
    filename: str
    file_type: str
    file_size_bytes: int
    upload_status: str
    message: str


# ── Documents ─────────────────────────────────────────────────────────────────

class DocumentOut(BaseModel):
    id: uuid.UUID
    chatbot_id: uuid.UUID
    workspace_id: uuid.UUID
    filename: str
    original_filename: str
    file_type: str
    file_size_bytes: int
    upload_status: str          # pending|uploaded|processing|completed|failed|deleted
    error_message: str | None
    chunk_count: int
    uploaded_at: datetime
    processed_at: datetime | None

    model_config = {"from_attributes": True}


# ── Ingestion jobs ────────────────────────────────────────────────────────────

class IngestionJobOut(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    chatbot_id: uuid.UUID
    workspace_id: uuid.UUID
    celery_task_id: str | None
    job_status: str             # queued|validating|parsing|chunking|embedding|upserting|completed|failed
    progress_percent: int
    chunks_created: int
    error_message: str | None
    queued_at: datetime
    started_at: datetime | None
    completed_at: datetime | None

    model_config = {"from_attributes": True}


# ── Knowledge base stats ──────────────────────────────────────────────────────

class KnowledgeBaseStats(BaseModel):
    chatbot_id: uuid.UUID
    workspace_id: uuid.UUID
    qdrant_collection_name: str
    total_documents: int
    total_chunks: int
    storage_used_mb: float          # derived from storage_used_bytes
    last_synced_at: datetime | None


# ── Sync / Clear ──────────────────────────────────────────────────────────────

class SyncResponse(BaseModel):
    status: str
    chunks_synced: int
    documents_processed: int
    time_taken_ms: int


class ClearResponse(BaseModel):
    status: str
    documents_deleted: int
    chunks_deleted: int
    message: str


# ── Health ────────────────────────────────────────────────────────────────────

class ChatbotEngineHealth(BaseModel):
    status: str                     # ok|degraded|unhealthy
    qdrant_connected: bool
    celery_connected: bool
    version: str