"""
Pydantic schemas for Phase 4/5 — end-user chat and internal APIs.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


# ── Session ───────────────────────────────────────────────────────────────────

class CreateSessionRequest(BaseModel):
    # Caller-supplied opaque identifier (email, phone, uuid, or null for anon)
    end_user_id: str | None = Field(default=None, max_length=255)
    existing_session_id: uuid.UUID | None = Field(default=None, description="Non-sensitive identifier of an existing active session to restore.")
    metadata: dict[str, Any] = Field(default_factory=dict)


class SessionOut(BaseModel):
    id: uuid.UUID
    chatbot_id: uuid.UUID
    workspace_id: uuid.UUID
    end_user_id: str | None
    welcome_message: str | None = None
    brand_color: str | None = None
    chatbot_name: str | None = None
    session_status: str
    session_token: str          # returned ONCE — client stores this
    expires_at: datetime
    message_count: int
    total_tokens: int
    created_at: datetime

    model_config = {"from_attributes": True}


class EndSessionRequest(BaseModel):
    summarize: bool = True      # request chatbot-rag to summarize the conversation


class SessionEndedOut(BaseModel):
    session_id: uuid.UUID
    session_status: str
    duration_seconds: int | None
    message_count: int
    total_tokens: int
    session_summary: str | None


# ── Messages ──────────────────────────────────────────────────────────────────

class MessageOut(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    role: str
    content: str
    tokens_input: int
    tokens_output: int
    confidence_score: Decimal | None
    sources: list | dict | None
    metadata_: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageListOut(BaseModel):
    messages: list[MessageOut]
    total: int
    limit: int
    offset: int


# ── WebSocket events ──────────────────────────────────────────────────────────
# These are NOT Pydantic models — they are plain dicts sent over the WebSocket.
# Documented here as TypedDict-style comments for clarity.

# Client → Server:
#   { "type": "message", "content": "What is the refund policy?" }

# Server → Client (streaming token):
#   { "type": "token", "content": "The " }

# Server → Client (complete response):
#   { "type": "response",
#     "content": "The refund policy is...",
#     "confidence": 0.92,
#     "sources": [...],
#     "clarification_question": null,
#     "tokens": { "input": 45, "output": 120 },
#     "execution_time_ms": 1340 }

# Server → Client (error):
#   { "type": "error", "code": "QUOTA_EXCEEDED", "message": "..." }

# Server → Client (session ended):
#   { "type": "session_ended", "reason": "expired" }


# ── Internal API schemas ──────────────────────────────────────────────────────

class ChatbotConfigInternal(BaseModel):
    """Full chatbot config returned to chatbot-rag via internal endpoint."""
    chatbot_id: uuid.UUID
    workspace_id: uuid.UUID
    llm_provider: str
    llm_model: str
    # Decrypted key — only returned over internal auth, never to frontend
    llm_api_key: str | None
    temperature: float
    max_tokens: int
    top_p: float
    system_prompt: str | None
    tone_preset: str
    memory_mode: str
    context_depth: int
    retrieval_top_k: int
    confidence_threshold: float
    qdrant_collection_name: str


class IngestionCallbackRequest(BaseModel):
    """Chatbot-rag calls this when an ingestion job status changes."""
    job_status: str
    chunks_created: int = 0
    error_message: str | None = None
    progress_percent: int = 0


class TokenUsageRequest(BaseModel):
    """Chatbot-rag logs token consumption after each response."""
    workspace_id: uuid.UUID
    chatbot_id: uuid.UUID
    session_id: uuid.UUID
    tokens_input: int
    tokens_output: int
    cost_usd: float = 0.0


class QuotaCheckRequest(BaseModel):
    estimated_tokens: int = Field(ge=1)


class QuotaCheckResponse(BaseModel):
    allowed: bool
    reason: str | None
    current_usage: int
    limit: int
    remaining_tokens: int


# ── Internal API key management ───────────────────────────────────────────────

class CreateInternalKeyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class InternalKeyOut(BaseModel):
    id: uuid.UUID
    name: str
    key_prefix: str
    raw_key: str | None = None   # set ONCE on creation, never again
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}