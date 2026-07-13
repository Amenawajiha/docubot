"""chat sessions, conversation messages, usage logs, internal API key

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-02

New tables:
  chat_sessions         — one row per end-user session with a chatbot
  chat_messages         — individual messages within a session
  workspace_usage_logs  — daily token/cost aggregates per workspace
  internal_api_keys     — backend-to-backend shared secrets
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:

    # ── chat_sessions ─────────────────────────────────────────────────────────
    op.create_table(
        "chat_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "chatbot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chatbots.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Nullable — anonymous end-users have no account
        sa.Column("end_user_id", sa.String(255), nullable=True),
        sa.Column(
            "session_status",
            sa.String(50),
            server_default="active",
            nullable=False,
        ),   # active|ended|expired
        # Auth token issued to the end-user for this session
        sa.Column("session_token", sa.String(255), nullable=False, unique=True),
        sa.Column("session_token_expires_at", sa.DateTime(timezone=True), nullable=False),
        # Stats — denormalised for fast reads
        sa.Column("message_count", sa.Integer(), server_default="0"),
        sa.Column("total_tokens", sa.Integer(), server_default="0"),
        sa.Column("session_summary", sa.Text(), nullable=True),
        # Context / fingerprinting
        sa.Column("metadata_", postgresql.JSONB(), server_default="{}"),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
    )
    op.create_index("idx_session_chatbot",    "chat_sessions", ["chatbot_id"])
    op.create_index("idx_session_workspace",  "chat_sessions", ["workspace_id"])
    op.create_index("idx_session_token",      "chat_sessions", ["session_token"])
    op.create_index("idx_session_end_user",   "chat_sessions", ["end_user_id"],
                    postgresql_where=sa.text("end_user_id IS NOT NULL"))
    op.create_index("idx_session_status",     "chat_sessions", ["session_status"])
    op.create_index("idx_session_expires_at", "chat_sessions", ["expires_at"])

    # ── chat_messages ─────────────────────────────────────────────────────────
    op.create_table(
        "chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "chatbot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chatbots.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("end_user_id", sa.String(255), nullable=True),
        sa.Column("role", sa.String(20), nullable=False),   # user|assistant|system
        sa.Column("content", sa.Text(), nullable=False),
        # Token tracking
        sa.Column("tokens_input", sa.Integer(), server_default="0"),
        sa.Column("tokens_output", sa.Integer(), server_default="0"),
        # RAG metadata
        sa.Column("confidence_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("sources", postgresql.JSONB(), nullable=True),
        # Misc metadata (clarification_asked, is_summary, execution_time_ms, etc.)
        sa.Column("metadata_", postgresql.JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_msg_session",   "chat_messages", ["session_id"])
    op.create_index("idx_msg_chatbot",   "chat_messages", ["chatbot_id"])
    op.create_index("idx_msg_workspace", "chat_messages", ["workspace_id", "created_at"])

    # ── workspace_usage_logs ──────────────────────────────────────────────────
    op.create_table(
        "workspace_usage_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "chatbot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chatbots.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chat_sessions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("log_date", sa.Date(), nullable=False),
        sa.Column("tokens_input", sa.Integer(), server_default="0"),
        sa.Column("tokens_output", sa.Integer(), server_default="0"),
        sa.Column("tokens_total", sa.Integer(), server_default="0"),
        sa.Column("cost_usd", sa.Numeric(10, 6), server_default="0"),
        sa.Column("message_count", sa.Integer(), server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_workspace_usage_logs_workspace_date", "workspace_usage_logs",
                    ["workspace_id", "log_date"])
    op.create_index("idx_workspace_usage_logs_chatbot_date",   "workspace_usage_logs",
                    ["chatbot_id", "log_date"])

    # ── internal_api_keys ────────────────────────────────────────────────────
    # Shared secrets for backend-to-backend calls (website ↔ chatbot-rag).
    # key_hash is bcrypt. The raw key is shown once and never stored.
    op.create_table(
        "internal_api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("key_prefix", sa.String(20), nullable=False),
        sa.Column("key_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_internal_key_prefix", "internal_api_keys", ["key_prefix"])


def downgrade() -> None:
    op.drop_table("internal_api_keys")
    op.drop_table("workspace_usage_logs")
    op.drop_table("chat_messages")
    op.drop_table("chat_sessions")