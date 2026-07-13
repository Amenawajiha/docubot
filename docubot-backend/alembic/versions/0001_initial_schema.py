"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-04-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── users ─────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255)),
        sa.Column("email_verified", sa.Boolean(), server_default="false"),
        sa.Column("email_verification_token", sa.String(255)),
        sa.Column("email_verification_expires_at", sa.DateTime(timezone=True)),
        sa.Column("password_reset_token", sa.String(255)),
        sa.Column("password_reset_expires_at", sa.DateTime(timezone=True)),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}"),
    )
    op.create_index("idx_users_email", "users", ["email"])
    op.create_index("idx_users_created_at", "users", ["created_at"])
    op.create_index(
        "idx_users_email_verification_token",
        "users",
        ["email_verification_token"],
        postgresql_where=sa.text("email_verification_token IS NOT NULL"),
    )
    op.create_index(
        "idx_users_password_reset_token",
        "users",
        ["password_reset_token"],
        postgresql_where=sa.text("password_reset_token IS NOT NULL"),
    )

    # ── workspaces ────────────────────────────────────────────────────────────
    op.create_table(
        "workspaces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), unique=True, nullable=False),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("plan_tier", sa.String(50), server_default="trial"),
        sa.Column("plan_status", sa.String(50), server_default="active"),
        sa.Column("trial_ends_at", sa.DateTime(timezone=True)),
        sa.Column("next_billing_date", sa.Date()),
        sa.Column("monthly_message_limit", sa.Integer(), server_default="5000"),
        sa.Column("chatbot_limit", sa.Integer(), server_default="10"),
        sa.Column("storage_limit_mb", sa.Integer(), server_default="50"),
        sa.Column("settings", postgresql.JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )
    op.create_index("idx_workspaces_owner", "workspaces", ["owner_id"])
    op.create_index("idx_workspaces_slug", "workspaces", ["slug"])
    op.create_index(
        "idx_workspaces_deleted_at",
        "workspaces",
        ["deleted_at"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # ── workspace_members ─────────────────────────────────────────────────────
    op.create_table(
        "workspace_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column(
            "invited_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column("invitation_token", sa.String(255)),
        sa.Column("invitation_expires_at", sa.DateTime(timezone=True)),
        sa.Column("invited_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("joined_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("workspace_id", "user_id", name="unique_workspace_user"),
    )
    op.create_index("idx_workspace_members_workspace", "workspace_members", ["workspace_id"])
    op.create_index("idx_workspace_members_user", "workspace_members", ["user_id"])
    op.create_index(
        "idx_workspace_members_invitation_token",
        "workspace_members",
        ["invitation_token"],
        postgresql_where=sa.text("invitation_token IS NOT NULL"),
    )

    # ── chatbots ──────────────────────────────────────────────────────────────
    op.create_table(
        "chatbots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("avatar_emoji", sa.String(10), server_default="🤖"),
        sa.Column("brand_color", sa.String(7), server_default="#3B82F6"),
        sa.Column("llm_provider", sa.String(50), server_default="openai"),
        sa.Column("llm_model", sa.String(100), server_default="gpt-4o"),
        sa.Column("custom_api_key_encrypted", sa.Text()),
        sa.Column("temperature", sa.Numeric(3, 2), server_default="0.30"),
        sa.Column("max_tokens", sa.Integer(), server_default="500"),
        sa.Column("top_p", sa.Numeric(3, 2), server_default="0.90"),
        sa.Column("tone_preset", sa.String(50), server_default="friendly"),
        sa.Column("custom_system_prompt", sa.Text()),
        sa.Column("default_language", sa.String(10), server_default="auto"),
        sa.Column("fallback_language", sa.String(10), server_default="en"),
        sa.Column("widget_style", sa.String(50), server_default="bubble"),
        sa.Column(
            "welcome_message", sa.Text(), server_default="Hi! How can I help you today?"
        ),
        sa.Column(
            "input_placeholder", sa.Text(), server_default="Type your question here..."
        ),
        sa.Column("show_citations", sa.Boolean(), server_default="true"),
        sa.Column("memory_mode", sa.String(50), server_default="persistent"),
        sa.Column("context_depth", sa.Integer(), server_default="10"),
        sa.Column("retrieval_top_k", sa.Integer(), server_default="5"),
        sa.Column("confidence_threshold", sa.Numeric(3, 2), server_default="0.70"),
        sa.Column("auth_mode", sa.String(50), server_default="public"),
        sa.Column("passcode_hash", sa.String(255)),
        sa.Column("is_active", sa.Boolean(), server_default="false"),
        sa.Column("deployment_status", sa.String(50), server_default="draft"),
        sa.Column("total_messages", sa.Integer(), server_default="0"),
        sa.Column("total_conversations", sa.Integer(), server_default="0"),
        sa.Column("resolution_rate", sa.Numeric(5, 2)),
        sa.Column("avg_response_time_ms", sa.Integer()),
        sa.Column("avg_confidence_score", sa.Numeric(5, 2)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_trained_at", sa.DateTime(timezone=True)),
        sa.Column("last_deployed_at", sa.DateTime(timezone=True)),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )
    op.create_index("idx_chatbots_workspace", "chatbots", ["workspace_id"])
    op.create_index("idx_chatbots_active", "chatbots", ["workspace_id", "is_active"])
    op.create_index("idx_chatbots_created_at", "chatbots", ["created_at"])
    op.create_index(
        "idx_chatbots_deleted_at",
        "chatbots",
        ["deleted_at"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # ── knowledge_sources ────────────────────────────────────────────────────
    op.create_table(
        "knowledge_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "chatbot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chatbots.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("source_name", sa.String(255), nullable=False),
        sa.Column("file_type", sa.String(50)),
        sa.Column("file_size_bytes", sa.BigInteger()),
        sa.Column("file_url", sa.Text()),
        sa.Column("crawled_url", sa.Text()),
        sa.Column("url_pattern", sa.Text()),
        sa.Column("processing_status", sa.String(50), server_default="pending"),
        sa.Column("total_chunks", sa.Integer(), server_default="0"),
        sa.Column("error_message", sa.Text()),
        sa.Column("version", sa.Integer(), server_default="1"),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("processed_at", sa.DateTime(timezone=True)),
        sa.Column("last_synced_at", sa.DateTime(timezone=True)),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )
    op.create_index("idx_sources_chatbot", "knowledge_sources", ["chatbot_id"])
    op.create_index("idx_sources_workspace", "knowledge_sources", ["workspace_id"])
    op.create_index("idx_sources_status", "knowledge_sources", ["processing_status"])
    op.create_index(
        "idx_sources_deleted_at",
        "knowledge_sources",
        ["deleted_at"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # ── knowledge_chunks ─────────────────────────────────────────────────────
    op.create_table(
        "knowledge_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("knowledge_sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "chatbot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chatbots.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("chunk_metadata", postgresql.JSONB(), server_default="{}"),
        sa.Column("qdrant_point_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("qdrant_collection_name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_chunks_source", "knowledge_chunks", ["source_id"])
    op.create_index("idx_chunks_chatbot", "knowledge_chunks", ["chatbot_id"])
    op.create_index(
        "idx_chunks_qdrant",
        "knowledge_chunks",
        ["qdrant_collection_name", "qdrant_point_id"],
    )

    # ── end_user_sessions ────────────────────────────────────────────────────
    op.create_table(
        "end_user_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "chatbot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chatbots.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("session_token", sa.String(255), unique=True, nullable=False),
        sa.Column("end_user_id", sa.String(255)),
        sa.Column("end_user_metadata", postgresql.JSONB(), server_default="{}"),
        sa.Column("ip_address", postgresql.INET()),
        sa.Column("user_agent", sa.Text()),
        sa.Column("referrer", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "last_activity_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
    )
    op.create_index("idx_sessions_chatbot", "end_user_sessions", ["chatbot_id"])
    op.create_index("idx_sessions_workspace", "end_user_sessions", ["workspace_id"])
    op.create_index("idx_sessions_token", "end_user_sessions", ["session_token"])
    op.create_index("idx_sessions_started_at", "end_user_sessions", ["started_at"])

    # ── conversations ────────────────────────────────────────────────────────
    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("end_user_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "chatbot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chatbots.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("first_message_preview", sa.Text()),
        sa.Column("total_messages", sa.Integer(), server_default="0"),
        sa.Column("avg_confidence_score", sa.Numeric(5, 2)),
        sa.Column("total_tokens_used", sa.Integer(), server_default="0"),
        sa.Column("resolution_status", sa.String(50), server_default="active"),
        sa.Column("escalation_reason", sa.Text()),
        sa.Column("user_rating", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "idx_conversations_chatbot", "conversations", ["chatbot_id", "created_at"]
    )
    op.create_index(
        "idx_conversations_workspace", "conversations", ["workspace_id", "created_at"]
    )
    op.create_index("idx_conversations_status", "conversations", ["resolution_status"])

    # ── messages ─────────────────────────────────────────────────────────────
    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "chatbot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chatbots.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("confidence_score", sa.Numeric(5, 2)),
        sa.Column("sources_cited", postgresql.JSONB()),
        sa.Column("tokens_used", sa.Integer()),
        sa.Column("response_time_ms", sa.Integer()),
        sa.Column("llm_model_used", sa.String(100)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_messages_conversation", "messages", ["conversation_id"])
    op.create_index(
        "idx_messages_workspace_date", "messages", ["workspace_id", "created_at"]
    )
    op.create_index("idx_messages_created_at", "messages", ["created_at"])

    # ── usage_events ─────────────────────────────────────────────────────────
    op.create_table(
        "usage_events",
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
        ),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("event_data", postgresql.JSONB(), nullable=False),
        sa.Column("tokens_used", sa.Integer()),
        sa.Column("estimated_cost_usd", sa.Numeric(10, 6)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "idx_usage_workspace_date", "usage_events", ["workspace_id", "created_at"]
    )
    op.create_index(
        "idx_usage_chatbot_date", "usage_events", ["chatbot_id", "created_at"]
    )
    op.create_index("idx_usage_created_at", "usage_events", ["created_at"])

    # ── workspace_usage_summary ───────────────────────────────────────────────
    op.create_table(
        "workspace_usage_summary",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("billing_period_start", sa.Date(), nullable=False),
        sa.Column("billing_period_end", sa.Date(), nullable=False),
        sa.Column("total_messages", sa.Integer(), server_default="0"),
        sa.Column("total_conversations", sa.Integer(), server_default="0"),
        sa.Column("total_tokens_used", sa.BigInteger(), server_default="0"),
        sa.Column("total_cost_usd", sa.Numeric(10, 2), server_default="0.00"),
        sa.Column("storage_used_mb", sa.Integer(), server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "workspace_id",
            "billing_period_start",
            name="unique_workspace_billing_period",
        ),
    )
    op.create_index(
        "idx_usage_summary_workspace", "workspace_usage_summary", ["workspace_id"]
    )

    # ── daily_metrics ─────────────────────────────────────────────────────────
    op.create_table(
        "daily_metrics",
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
        ),
        sa.Column("metric_date", sa.Date(), nullable=False),
        sa.Column("total_messages", sa.Integer(), server_default="0"),
        sa.Column("total_conversations", sa.Integer(), server_default="0"),
        sa.Column("unique_users", sa.Integer(), server_default="0"),
        sa.Column("resolved_conversations", sa.Integer(), server_default="0"),
        sa.Column("escalated_conversations", sa.Integer(), server_default="0"),
        sa.Column("avg_response_time_ms", sa.Integer()),
        sa.Column("avg_confidence_score", sa.Numeric(5, 2)),
        sa.Column("total_tokens_used", sa.Integer(), server_default="0"),
        sa.Column("total_cost_usd", sa.Numeric(10, 4), server_default="0.00"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "workspace_id",
            "chatbot_id",
            "metric_date",
            name="unique_workspace_chatbot_date",
        ),
    )
    op.create_index(
        "idx_metrics_workspace_date", "daily_metrics", ["workspace_id", "metric_date"]
    )
    op.create_index(
        "idx_metrics_chatbot_date", "daily_metrics", ["chatbot_id", "metric_date"]
    )

    # ── hourly_heatmap ────────────────────────────────────────────────────────
    op.create_table(
        "hourly_heatmap",
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
        ),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("hour_of_day", sa.Integer(), nullable=False),
        sa.Column("conversation_count", sa.Integer(), server_default="0"),
        sa.Column("message_count", sa.Integer(), server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "workspace_id",
            "chatbot_id",
            "week_start",
            "day_of_week",
            "hour_of_day",
            name="unique_heatmap_entry",
        ),
    )
    op.create_index("idx_heatmap_workspace", "hourly_heatmap", ["workspace_id", "week_start"])
    op.create_index("idx_heatmap_chatbot", "hourly_heatmap", ["chatbot_id", "week_start"])

    # ── deployment_channels ───────────────────────────────────────────────────
    op.create_table(
        "deployment_channels",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "chatbot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chatbots.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("channel_type", sa.String(100), nullable=False),
        sa.Column("channel_config", postgresql.JSONB(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("last_sync_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_channels_chatbot", "deployment_channels", ["chatbot_id"])
    op.create_index("idx_channels_type", "deployment_channels", ["channel_type"])

    # ── api_keys ──────────────────────────────────────────────────────────────
    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("key_name", sa.String(255), nullable=False),
        sa.Column("key_prefix", sa.String(20), nullable=False),
        sa.Column("key_hash", sa.String(255), nullable=False),
        sa.Column("permissions", postgresql.JSONB(), server_default='["chat"]'),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_apikeys_workspace", "api_keys", ["workspace_id"])
    op.create_index("idx_apikeys_prefix", "api_keys", ["key_prefix"])

    # ── invoices ──────────────────────────────────────────────────────────────
    op.create_table(
        "invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("invoice_number", sa.String(50), unique=True, nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("amount_usd", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", sa.String(50), server_default="pending"),
        sa.Column("line_items", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("paid_at", sa.DateTime(timezone=True)),
    )
    op.create_index("idx_invoices_workspace", "invoices", ["workspace_id"])
    op.create_index("idx_invoices_period", "invoices", ["period_start", "period_end"])

    # ── activity_feed ─────────────────────────────────────────────────────────
    op.create_table(
        "activity_feed",
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
        ),
        sa.Column("activity_type", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "idx_activity_workspace_date", "activity_feed", ["workspace_id", "created_at"]
    )

    # ── bot_templates ─────────────────────────────────────────────────────────
    op.create_table(
        "bot_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("is_official", sa.Boolean(), server_default="false"),
        sa.Column("rating", sa.Numeric(3, 2)),
        sa.Column("use_count", sa.Integer(), server_default="0"),
        sa.Column("template_config", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_templates_category", "bot_templates", ["category"])

    # ── audit_logs ────────────────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(100)),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True)),
        sa.Column("ip_address", postgresql.INET()),
        sa.Column("user_agent", sa.Text()),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_audit_workspace", "audit_logs", ["workspace_id", "created_at"])
    op.create_index("idx_audit_user", "audit_logs", ["user_id", "created_at"])
    op.create_index("idx_audit_action", "audit_logs", ["action", "created_at"])

    # ── deleted_workspaces_cleanup ────────────────────────────────────────────
    op.create_table(
        "deleted_workspaces_cleanup",
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scheduled_hard_delete_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "qdrant_collections_deleted", sa.Boolean(), server_default="false"
        ),
        sa.Column("s3_files_deleted", sa.Boolean(), server_default="false"),
    )
    op.create_index(
        "idx_cleanup_scheduled",
        "deleted_workspaces_cleanup",
        ["scheduled_hard_delete_at"],
        postgresql_where=sa.text(
            "qdrant_collections_deleted = TRUE AND s3_files_deleted = TRUE"
        ),
    )

    # ── Performance indexes from §8.1 ────────────────────────────────────────
    op.create_index(
        "idx_usage_workspace_date_include",
        "usage_events",
        ["workspace_id", "created_at"],
        postgresql_include=["tokens_used", "estimated_cost_usd"],
    )
    op.create_index(
        "idx_conversations_status_date",
        "conversations",
        ["resolution_status", "created_at"],
    )


def downgrade() -> None:
    # Drop in reverse dependency order
    tables = [
        "deleted_workspaces_cleanup",
        "audit_logs",
        "bot_templates",
        "activity_feed",
        "invoices",
        "api_keys",
        "deployment_channels",
        "hourly_heatmap",
        "daily_metrics",
        "workspace_usage_summary",
        "usage_events",
        "messages",
        "conversations",
        "end_user_sessions",
        "knowledge_chunks",
        "knowledge_sources",
        "chatbots",
        "workspace_members",
        "workspaces",
        "users",
    ]
    for table in tables:
        op.drop_table(table)