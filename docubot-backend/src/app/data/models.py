"""
SQLAlchemy ORM models — mirrors the PostgreSQL schema defined in the
Backend Architecture & DB Design document exactly.
"""

import uuid
from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.data.database import Base


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _uuid() -> uuid.UUID:
    return uuid.uuid4()


# ─────────────────────────────────────────────────────────────────────────────
# 3.1  Authentication & Workspaces
# ─────────────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255))

    # OAuth fields - None for email/password users
    oauth_provider: Mapped[str | None] = mapped_column(String(50))
    oauth_provider_id: Mapped[str | None] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(Text)

    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    email_verification_token: Mapped[str | None] = mapped_column(String(255))
    email_verification_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    password_reset_token: Mapped[str | None] = mapped_column(String(255))
    password_reset_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, default=dict, server_default="{}"
    )

    @property
    def password_last_changed(self) -> datetime | None:
        val = self.metadata_.get("password_last_changed")
        if val:
            try:
                return datetime.fromisoformat(val)
            except Exception:
                pass
        return self.created_at


    # Relationships
    owned_workspaces: Mapped[list["Workspace"]] = relationship(
        "Workspace", back_populates="owner", foreign_keys="Workspace.owner_id"
    )
    workspace_memberships: Mapped[list["WorkspaceMember"]] = relationship(
        "WorkspaceMember", back_populates="user", foreign_keys="WorkspaceMember.user_id"
    )

    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_created_at", "created_at"),
        Index(
            "idx_users_email_verification_token",
            "email_verification_token",
            postgresql_where="email_verification_token IS NOT NULL",
        ),
        Index(
            "idx_users_password_reset_token",
            "password_reset_token",
            postgresql_where="password_reset_token IS NOT NULL",
        ),
        Index(
            "idx_users_oauth", 
            "oauth_provider",
            "oauth_provider_id",
            postgresql_where="oauth_provider IS NOT NULL",
        ),
    )


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Billing
    plan_tier: Mapped[str] = mapped_column(String(50), default="trial")
    plan_status: Mapped[str] = mapped_column(String(50), default="active")
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_billing_date: Mapped[datetime | None] = mapped_column(Date)

    # Usage Limits
    monthly_message_limit: Mapped[int] = mapped_column(Integer, default=5000)
    chatbot_limit: Mapped[int] = mapped_column(Integer, default=10)
    storage_limit_mb: Mapped[int] = mapped_column(Integer, default=50)

    settings: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    owner: Mapped["User"] = relationship(
        "User", back_populates="owned_workspaces", foreign_keys=[owner_id]
    )
    members: Mapped[list["WorkspaceMember"]] = relationship(
        "WorkspaceMember", back_populates="workspace"
    )
    chatbots: Mapped[list["Chatbot"]] = relationship(
        "Chatbot", back_populates="workspace"
    )

    __table_args__ = (
        Index("idx_workspaces_owner", "owner_id"),
        Index("idx_workspaces_slug", "slug"),
        Index(
            "idx_workspaces_deleted_at",
            "deleted_at",
            postgresql_where="deleted_at IS NULL",
        ),
    )


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False)  # admin|editor|viewer
    invited_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    invitation_token: Mapped[str | None] = mapped_column(String(255))
    invitation_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    invited_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    workspace: Mapped["Workspace"] = relationship(
        "Workspace", back_populates="members"
    )
    user: Mapped["User"] = relationship(
        "User", back_populates="workspace_memberships", foreign_keys=[user_id]
    )

    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="unique_workspace_user"),
        Index("idx_workspace_members_workspace", "workspace_id"),
        Index("idx_workspace_members_user", "user_id"),
        Index(
            "idx_workspace_members_invitation_token",
            "invitation_token",
            postgresql_where="invitation_token IS NOT NULL",
        ),
    )



class WorkspaceInvitation(Base):
    __tablename__ = "workspace_invitations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)  # admin|editor|viewer
    invited_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    invitation_token: Mapped[str] = mapped_column(String(255), nullable=False)
    invitation_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    invited_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("workspace_id", "email", name="unique_workspace_invitation_email"),
        Index("idx_workspace_invitations_workspace", "workspace_id"),
        Index(
            "idx_workspace_invitations_token",
            "invitation_token",
        ),
    )

# ─────────────────────────────────────────────────────────────────────────────
# 3.2  Chatbot Configuration
# ─────────────────────────────────────────────────────────────────────────────

class Chatbot(Base):
    __tablename__ = "chatbots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Identity
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_emoji: Mapped[str] = mapped_column(String(10), default="🤖")
    brand_color: Mapped[str] = mapped_column(String(7), default="#3B82F6")

    # LLM Configuration
    llm_provider: Mapped[str] = mapped_column(String(50), default="openai")
    llm_model: Mapped[str] = mapped_column(String(100), default="gpt-4o")
    custom_api_key_encrypted: Mapped[str | None] = mapped_column(Text)
    temperature: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=Decimal("0.30"))
    max_tokens: Mapped[int] = mapped_column(Integer, default=500)
    top_p: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=Decimal("0.90"))

    # Personality
    tone_preset: Mapped[str] = mapped_column(String(50), default="friendly")
    custom_system_prompt: Mapped[str | None] = mapped_column(Text)

    # Language
    default_language: Mapped[str] = mapped_column(String(10), default="auto")
    fallback_language: Mapped[str] = mapped_column(String(10), default="en")

    # Widget
    widget_style: Mapped[str] = mapped_column(String(50), default="bubble")
    welcome_message: Mapped[str] = mapped_column(
        Text, default="Hi! How can I help you today?"
    )
    input_placeholder: Mapped[str] = mapped_column(
        Text, default="Type your question here..."
    )
    show_citations: Mapped[bool] = mapped_column(Boolean, default=True)

    # Memory & Context
    memory_mode: Mapped[str] = mapped_column(String(50), default="persistent")
    context_depth: Mapped[int] = mapped_column(Integer, default=10)

    # RAG
    retrieval_top_k: Mapped[int] = mapped_column(Integer, default=5)
    confidence_threshold: Mapped[Decimal] = mapped_column(
        Numeric(3, 2), default=Decimal("0.70")
    )

    # Access
    auth_mode: Mapped[str] = mapped_column(String(50), default="public")
    passcode_hash: Mapped[str | None] = mapped_column(String(255))

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    deployment_status: Mapped[str] = mapped_column(String(50), default="draft")

    # Cached Stats
    total_messages: Mapped[int] = mapped_column(Integer, default=0)
    total_conversations: Mapped[int] = mapped_column(Integer, default=0)
    resolution_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    avg_response_time_ms: Mapped[int | None] = mapped_column(Integer)
    avg_confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    last_trained_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_deployed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="chatbots")
    knowledge_sources: Mapped[list["KnowledgeSource"]] = relationship(
        "KnowledgeSource", back_populates="chatbot"
    )

    __table_args__ = (
        Index("idx_chatbots_workspace", "workspace_id"),
        Index("idx_chatbots_active", "workspace_id", "is_active"),
        Index("idx_chatbots_created_at", "created_at"),
        Index(
            "idx_chatbots_deleted_at",
            "deleted_at",
            postgresql_where="deleted_at IS NULL",
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3.3  Knowledge Base
# ─────────────────────────────────────────────────────────────────────────────

class KnowledgeSource(Base):
    __tablename__ = "knowledge_sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    chatbot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chatbots.id", ondelete="CASCADE"),
        nullable=False,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )

    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)

    file_type: Mapped[str | None] = mapped_column(String(50))
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    file_url: Mapped[str | None] = mapped_column(Text)

    crawled_url: Mapped[str | None] = mapped_column(Text)
    url_pattern: Mapped[str | None] = mapped_column(Text)

    processing_status: Mapped[str] = mapped_column(String(50), default="pending")
    total_chunks: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    chatbot: Mapped["Chatbot"] = relationship(
        "Chatbot", back_populates="knowledge_sources"
    )
    chunks: Mapped[list["KnowledgeChunk"]] = relationship(
        "KnowledgeChunk", back_populates="source"
    )

    __table_args__ = (
        Index("idx_sources_chatbot", "chatbot_id"),
        Index("idx_sources_workspace", "workspace_id"),
        Index("idx_sources_status", "processing_status"),
        Index(
            "idx_sources_deleted_at",
            "deleted_at",
            postgresql_where="deleted_at IS NULL",
        ),
    )


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_sources.id", ondelete="CASCADE"),
        nullable=False,
    )
    chatbot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chatbots.id", ondelete="CASCADE"),
        nullable=False,
    )

    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")

    qdrant_point_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    qdrant_collection_name: Mapped[str] = mapped_column(String(255), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    source: Mapped["KnowledgeSource"] = relationship(
        "KnowledgeSource", back_populates="chunks"
    )

    __table_args__ = (
        Index("idx_chunks_source", "source_id"),
        Index("idx_chunks_chatbot", "chatbot_id"),
        Index("idx_chunks_qdrant", "qdrant_collection_name", "qdrant_point_id"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3.4  Conversations & Messages
# ─────────────────────────────────────────────────────────────────────────────

class EndUserSession(Base):
    __tablename__ = "end_user_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    chatbot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chatbots.id", ondelete="CASCADE"),
        nullable=False,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )

    session_token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    end_user_id: Mapped[str | None] = mapped_column(String(255))
    end_user_metadata: Mapped[dict] = mapped_column(
        JSONB, default=dict, server_default="{}"
    )

    ip_address: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(Text)
    referrer: Mapped[str | None] = mapped_column(Text)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("idx_sessions_chatbot", "chatbot_id"),
        Index("idx_sessions_workspace", "workspace_id"),
        Index("idx_sessions_token", "session_token"),
        Index("idx_sessions_started_at", "started_at"),
    )


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("end_user_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    chatbot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chatbots.id", ondelete="CASCADE"),
        nullable=False,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )

    first_message_preview: Mapped[str | None] = mapped_column(Text)
    total_messages: Mapped[int] = mapped_column(Integer, default=0)
    avg_confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    total_tokens_used: Mapped[int] = mapped_column(Integer, default=0)

    resolution_status: Mapped[str] = mapped_column(String(50), default="active")
    escalation_reason: Mapped[str | None] = mapped_column(Text)
    user_rating: Mapped[int | None] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="conversation"
    )

    __table_args__ = (
        Index("idx_conversations_chatbot", "chatbot_id", "created_at"),
        Index("idx_conversations_workspace", "workspace_id", "created_at"),
        Index("idx_conversations_status", "resolution_status"),
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    chatbot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chatbots.id", ondelete="CASCADE"),
        nullable=False,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )

    role: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Assistant-only metadata
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    sources_cited: Mapped[dict | None] = mapped_column(JSONB)
    tokens_used: Mapped[int | None] = mapped_column(Integer)
    response_time_ms: Mapped[int | None] = mapped_column(Integer)
    llm_model_used: Mapped[str | None] = mapped_column(String(100))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="messages"
    )

    __table_args__ = (
        Index("idx_messages_conversation", "conversation_id"),
        Index("idx_messages_workspace_date", "workspace_id", "created_at"),
        Index("idx_messages_created_at", "created_at"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3.5  Analytics & Usage
# ─────────────────────────────────────────────────────────────────────────────

class UsageEvent(Base):
    __tablename__ = "usage_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    chatbot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chatbots.id", ondelete="SET NULL")
    )

    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    event_data: Mapped[dict] = mapped_column(JSONB, nullable=False)

    tokens_used: Mapped[int | None] = mapped_column(Integer)
    estimated_cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("idx_usage_workspace_date", "workspace_id", "created_at"),
        Index("idx_usage_chatbot_date", "chatbot_id", "created_at"),
        Index("idx_usage_created_at", "created_at"),
    )


class WorkspaceUsageSummary(Base):
    __tablename__ = "workspace_usage_summary"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )

    billing_period_start: Mapped[datetime] = mapped_column(Date, nullable=False)
    billing_period_end: Mapped[datetime] = mapped_column(Date, nullable=False)

    total_messages: Mapped[int] = mapped_column(Integer, default=0)
    total_conversations: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens_used: Mapped[int] = mapped_column(BigInteger, default=0)
    total_cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0.00")
    )
    storage_used_mb: Mapped[int] = mapped_column(Integer, default=0)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "billing_period_start",
            name="unique_workspace_billing_period",
        ),
        Index("idx_usage_summary_workspace", "workspace_id"),
    )


class DailyMetric(Base):
    __tablename__ = "daily_metrics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    chatbot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chatbots.id", ondelete="SET NULL")
    )

    metric_date: Mapped[datetime] = mapped_column(Date, nullable=False)

    total_messages: Mapped[int] = mapped_column(Integer, default=0)
    total_conversations: Mapped[int] = mapped_column(Integer, default=0)
    unique_users: Mapped[int] = mapped_column(Integer, default=0)
    resolved_conversations: Mapped[int] = mapped_column(Integer, default=0)
    escalated_conversations: Mapped[int] = mapped_column(Integer, default=0)
    avg_response_time_ms: Mapped[int | None] = mapped_column(Integer)
    avg_confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    total_tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    total_cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), default=Decimal("0.00")
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "chatbot_id",
            "metric_date",
            name="unique_workspace_chatbot_date",
        ),
        Index("idx_metrics_workspace_date", "workspace_id", "metric_date"),
        Index("idx_metrics_chatbot_date", "chatbot_id", "metric_date"),
    )


class HourlyHeatmap(Base):
    __tablename__ = "hourly_heatmap"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    chatbot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chatbots.id", ondelete="SET NULL")
    )

    week_start: Mapped[datetime] = mapped_column(Date, nullable=False)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    hour_of_day: Mapped[int] = mapped_column(Integer, nullable=False)

    conversation_count: Mapped[int] = mapped_column(Integer, default=0)
    message_count: Mapped[int] = mapped_column(Integer, default=0)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "chatbot_id",
            "week_start",
            "day_of_week",
            "hour_of_day",
            name="unique_heatmap_entry",
        ),
        Index("idx_heatmap_workspace", "workspace_id", "week_start"),
        Index("idx_heatmap_chatbot", "chatbot_id", "week_start"),
    )

# ─────────────────────────────────────────────────────────────────────────────
# 3.8  Activity Feed, Templates & Audit Logs
# ─────────────────────────────────────────────────────────────────────────────

class ActivityFeed(Base):
    __tablename__ = "activity_feed"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    chatbot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chatbots.id", ondelete="SET NULL")
    )

    activity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, default=dict, server_default="{}"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("idx_activity_workspace_date", "workspace_id", "created_at"),
    )


class BotTemplate(Base):
    __tablename__ = "bot_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    is_official: Mapped[bool] = mapped_column(Boolean, default=False)
    rating: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    use_count: Mapped[int] = mapped_column(Integer, default=0)

    template_config: Mapped[dict] = mapped_column(JSONB, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (Index("idx_templates_category", "category"),)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="SET NULL")
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )

    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(100))
    resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    ip_address: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, default=dict, server_default="{}"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("idx_audit_workspace", "workspace_id", "created_at"),
        Index("idx_audit_user", "user_id", "created_at"),
        Index("idx_audit_action", "action", "created_at"),
    )


class ChatbotDocument(Base):  # type: ignore[name-defined]  # Base from models.py
    __tablename__ = "chatbot_documents"
 
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    chatbot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chatbots.id", ondelete="CASCADE"),
        nullable=False,
    )
 
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    storage_key: Mapped[str | None] = mapped_column(Text)
 
    upload_status: Mapped[str] = mapped_column(String(50), server_default="pending")
    error_message: Mapped[str | None] = mapped_column(Text)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
 
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
 
    # Relationships
    ingestion_jobs: Mapped[list["IngestionJob"]] = relationship(
        "IngestionJob", back_populates="document"
    )
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        "DocumentChunk", back_populates="document"
    )
 
    __table_args__ = (
        Index("idx_docs_chatbot", "chatbot_id"),
        Index("idx_docs_workspace", "workspace_id"),
        Index("idx_docs_status", "upload_status"),
        Index(
            "idx_docs_not_deleted",
            "chatbot_id",
            "deleted_at",
            postgresql_where="deleted_at IS NULL",
        ),
    )
 
 
class IngestionJob(Base):  # type: ignore[name-defined]
    __tablename__ = "ingestion_jobs"
 
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    chatbot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chatbots.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chatbot_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
 
    celery_task_id: Mapped[str | None] = mapped_column(String(255))
    job_status: Mapped[str] = mapped_column(String(50), server_default="queued")
    progress_percent: Mapped[int] = mapped_column(Integer, default=0)
    chunks_created: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
 
    queued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
 
    document: Mapped["ChatbotDocument"] = relationship(
        "ChatbotDocument", back_populates="ingestion_jobs"
    )
 
    __table_args__ = (
        Index("idx_jobs_chatbot", "chatbot_id"),
        Index("idx_jobs_document", "document_id"),
        Index("idx_jobs_status", "job_status"),
        Index(
            "idx_jobs_celery_task",
            "celery_task_id",
            postgresql_where="celery_task_id IS NOT NULL",
        ),
    )
 
 
class DocumentChunk(Base):  # type: ignore[name-defined]
    __tablename__ = "document_chunks"
 
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chatbot_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    chatbot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chatbots.id", ondelete="CASCADE"),
        nullable=False,
    )
 
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text_content: Mapped[str] = mapped_column(Text, nullable=False)
    qdrant_point_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    qdrant_collection_name: Mapped[str] = mapped_column(String(255), nullable=False)
 
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
 
    document: Mapped["ChatbotDocument"] = relationship(
        "ChatbotDocument", back_populates="chunks"
    )
 
    __table_args__ = (
        Index("idx_chunks_document", "document_id"),
        Index("idx_chunks_chatbot", "chatbot_id"),
        Index("idx_chunks_qdrant", "qdrant_collection_name", "qdrant_point_id"),
    )
 
 
class ChatbotCollection(Base):  # type: ignore[name-defined]
    """
    Registry of Qdrant collections — one per chatbot.
    Also serves as a denormalised stats cache updated after every ingestion.
    Collection name format: workspace_{workspace_id}_chatbot_{chatbot_id}
    """
    __tablename__ = "chatbot_collections"
 
    chatbot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chatbots.id", ondelete="CASCADE"),
        primary_key=True,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
 
    qdrant_collection_name: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True
    )
    total_documents: Mapped[int] = mapped_column(Integer, default=0)
    total_chunks: Mapped[int] = mapped_column(Integer, default=0)
    storage_used_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
 
    __table_args__ = (
        Index("idx_collections_workspace", "workspace_id"),
        Index("idx_collections_name", "qdrant_collection_name", unique=True),
    )


class ChatSession(Base):  # type: ignore[name-defined]
    __tablename__ = "chat_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    chatbot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chatbots.id", ondelete="CASCADE"),
        nullable=False,
    )
    end_user_id: Mapped[str | None] = mapped_column(String(255))
    session_status: Mapped[str] = mapped_column(String(50), server_default="active")
    session_token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    session_token_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    session_summary: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict] = mapped_column(
        "metadata_", JSONB, default=dict, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)

    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage", back_populates="session"
    )

    __table_args__ = (
        Index("idx_session_chatbot",    "chatbot_id"),
        Index("idx_session_workspace",  "workspace_id"),
        Index("idx_session_token",      "session_token"),
        Index("idx_session_status",     "session_status"),
        Index("idx_session_expires_at", "expires_at"),
        Index(
            "idx_session_end_user",
            "end_user_id",
            postgresql_where="end_user_id IS NOT NULL",
        ),
    )


class ChatMessage(Base):  # type: ignore[name-defined]
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    chatbot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chatbots.id", ondelete="CASCADE"),
        nullable=False,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    end_user_id: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tokens_input: Mapped[int] = mapped_column(Integer, default=0)
    tokens_output: Mapped[int] = mapped_column(Integer, default=0)
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    sources: Mapped[dict | None] = mapped_column(JSONB)
    metadata_: Mapped[dict] = mapped_column(
        "metadata_", JSONB, default=dict, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    session: Mapped["ChatSession"] = relationship(
        "ChatSession", back_populates="messages"
    )

    __table_args__ = (
        Index("idx_msg_session",   "session_id"),
        Index("idx_msg_chatbot",   "chatbot_id"),
        Index("idx_msg_workspace", "workspace_id", "created_at"),
    )


class WorkspaceUsageLog(Base):  # type: ignore[name-defined]
    __tablename__ = "workspace_usage_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    chatbot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chatbots.id", ondelete="SET NULL"),
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="SET NULL"),
    )
    log_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    tokens_input: Mapped[int] = mapped_column(Integer, default=0)
    tokens_output: Mapped[int] = mapped_column(Integer, default=0)
    tokens_total: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 6), default=Decimal("0"))
    message_count: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("idx_usage_workspace_date", "workspace_id", "log_date"),
        Index("idx_usage_chatbot_date",   "chatbot_id",   "log_date"),
    )


class InternalApiKey(Base):  # type: ignore[name-defined]
    __tablename__ = "internal_api_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(20), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("idx_internal_key_prefix", "key_prefix"),
    )

class AnalyticsEvent(Base):  # type: ignore[name-defined]
    __tablename__ = "analytics_events"
 
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    chatbot_id:   Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chatbots.id",   ondelete="CASCADE"), nullable=False)
    session_id:   Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="SET NULL"))
    event_type:   Mapped[str]  = mapped_column(String(100), nullable=False)
    event_data:   Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    confidence_score:  Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    tokens_used:       Mapped[int]  = mapped_column(Integer, default=0)
    response_time_ms:  Mapped[int | None] = mapped_column(Integer)
    end_user_id:       Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
 
    __table_args__ = (
        Index("idx_events_chatbot_date",    "chatbot_id",   "created_at"),
        Index("idx_events_workspace_date",  "workspace_id", "created_at"),
        Index("idx_events_type",            "event_type"),
    )
 
 
class AnalyticsDaily(Base):  # type: ignore[name-defined]
    __tablename__ = "analytics_daily"
 
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    chatbot_id:   Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chatbots.id",   ondelete="CASCADE"), nullable=False)
    date:         Mapped[date] = mapped_column(Date, nullable=False)
    total_sessions:       Mapped[int] = mapped_column(Integer, default=0)
    total_messages:       Mapped[int] = mapped_column(Integer, default=0)
    unique_users:         Mapped[int] = mapped_column(Integer, default=0)
    avg_confidence:       Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    avg_response_time_ms: Mapped[int | None]     = mapped_column(Integer)
    total_tokens:         Mapped[int] = mapped_column(Integer, default=0)
    clarification_rate:   Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    resolution_rate:      Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    total_cost_usd:       Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
 
    __table_args__ = (
        UniqueConstraint("workspace_id", "chatbot_id", "date", name="uq_analytics_daily"),
        Index("idx_daily_chatbot_date",   "chatbot_id",   "date"),
        Index("idx_daily_workspace_date", "workspace_id", "date"),
    )
 
 
class DeploymentChannel(Base):  # type: ignore[name-defined]
    __tablename__ = "deployment_channels"
 
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    chatbot_id:   Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chatbots.id",   ondelete="CASCADE"), nullable=False)
    channel_type: Mapped[str] = mapped_column(String(50),  nullable=False)
    channel_name: Mapped[str] = mapped_column(String(255), nullable=False)
    config:           Mapped[dict]  = mapped_column(JSONB, default=dict, server_default="{}")
    allowed_domains:  Mapped[list]  = mapped_column(JSONB, default=list, server_default="[]")
    api_key_prefix:   Mapped[str | None] = mapped_column(String(20))
    api_key_hash:     Mapped[str | None] = mapped_column(String(255))
    is_active:  Mapped[bool]     = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
 
    __table_args__ = (
        Index("idx_deploy_chatbot", "chatbot_id"),
        Index("idx_deploy_type",    "channel_type"),
    )
 
 
class Plan(Base):  # type: ignore[name-defined]
    __tablename__ = "plans"
 
    id:   Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(50),  nullable=False, unique=True)
    price_monthly_usd:    Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    price_yearly_usd:     Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    chatbot_limit:        Mapped[int] = mapped_column(Integer, server_default="3")
    monthly_message_limit: Mapped[int] = mapped_column(Integer, server_default="5000")
    storage_limit_mb:     Mapped[int] = mapped_column(Integer, server_default="100")
    team_member_limit:    Mapped[int] = mapped_column(Integer, server_default="2")
    features:   Mapped[list]  = mapped_column(JSONB, default=list, server_default="[]")
    is_active:  Mapped[bool]  = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
 
 
class Subscription(Base):  # type: ignore[name-defined]
    __tablename__ = "subscriptions"
 
    id:           Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, unique=True)
    plan_id:      Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("plans.id", ondelete="RESTRICT"), nullable=False)
    status:          Mapped[str] = mapped_column(String(50), server_default="active")
    billing_cycle:   Mapped[str] = mapped_column(String(20), server_default="monthly")
    stripe_customer_id:     Mapped[str | None] = mapped_column(String(255))
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255))
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    current_period_end:   Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    canceled_at:   Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
 
    __table_args__ = (
        Index("idx_sub_workspace", "workspace_id"),
        Index("idx_sub_stripe_cust", "stripe_customer_id",
              postgresql_where="stripe_customer_id IS NOT NULL"),
    )
 
 
class Invoice(Base):  # type: ignore[name-defined]
    __tablename__ = "invoices"
 
    id:              Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    workspace_id:    Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id",    ondelete="CASCADE"), nullable=False)
    subscription_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("subscriptions.id", ondelete="SET NULL"))
    invoice_number:  Mapped[str]     = mapped_column(String(50), nullable=False, unique=True)
    status:   Mapped[str]     = mapped_column(String(50), server_default="draft")
    currency: Mapped[str]     = mapped_column(String(3),  server_default="USD")
    subtotal_usd: Mapped[Decimal] = mapped_column(Numeric(10, 2), server_default="0")
    tax_usd:      Mapped[Decimal] = mapped_column(Numeric(10, 2), server_default="0")
    total_usd:    Mapped[Decimal] = mapped_column(Numeric(10, 2), server_default="0")
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end:   Mapped[date] = mapped_column(Date, nullable=False)
    stripe_invoice_id: Mapped[str | None] = mapped_column(String(255))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    due_at:  Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
 
    line_items: Mapped[list["InvoiceLineItem"]] = relationship("InvoiceLineItem", back_populates="invoice")
 
    __table_args__ = (
        Index("idx_invoice_workspace", "workspace_id"),
        Index("idx_invoice_status",    "status"),
    )
 
 
class InvoiceLineItem(Base):  # type: ignore[name-defined]
    __tablename__ = "invoice_line_items"
 
    id:          Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    invoice_id:  Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    description: Mapped[str]     = mapped_column(Text,          nullable=False)
    quantity:    Mapped[int]     = mapped_column(Integer,       server_default="1")
    unit_price:  Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    amount_usd:  Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    item_type:   Mapped[str]     = mapped_column(String(50),    server_default="subscription")
    metadata_:   Mapped[dict]    = mapped_column("metadata_", JSONB, default=dict, server_default="{}")
 
    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="line_items")
 
    __table_args__ = (Index("idx_lineitems_invoice", "invoice_id"),)


# ─────────────────────────────────────────────────────────────────────────────
# 3.9  Soft Delete Cleanup
# ─────────────────────────────────────────────────────────────────────────────

class DeletedWorkspacesCleanup(Base):
    __tablename__ = "deleted_workspaces_cleanup"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True
    )
    deleted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    scheduled_hard_delete_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    qdrant_collections_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    s3_files_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        Index(
            "idx_cleanup_scheduled",
            "scheduled_hard_delete_at",
            postgresql_where=(
                "qdrant_collections_deleted = TRUE AND s3_files_deleted = TRUE"
            ),
        ),
    )

