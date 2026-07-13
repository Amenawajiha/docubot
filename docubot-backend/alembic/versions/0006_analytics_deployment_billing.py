"""analytics, deployment channels, billing tables

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-03

New tables:
  analytics_events     — raw per-message analytics events (time-series)
  analytics_daily      — pre-aggregated daily rollups per chatbot
  deployment_channels  — widget embed / REST API channel config
  plans                — billing plan definitions
  subscriptions        — workspace plan subscriptions
  invoices             — monthly billing records
  invoice_line_items   — per-line breakdown inside an invoice
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:

    # ── analytics_events ──────────────────────────────────────────────────────
    op.create_table(
        "analytics_events",
        sa.Column("id",           postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chatbot_id",   postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("chatbots.id",   ondelete="CASCADE"), nullable=False),
        sa.Column("session_id",   postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("chat_sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type",   sa.String(100), nullable=False),
        # session_started | message_sent | message_received | clarification_asked
        # session_ended | quota_exceeded | error | document_uploaded | chatbot_deployed
        sa.Column("event_data",   postgresql.JSONB(), server_default="{}"),
        sa.Column("confidence_score",    sa.Numeric(5, 2),  nullable=True),
        sa.Column("tokens_used",         sa.Integer(),      server_default="0"),
        sa.Column("response_time_ms",    sa.Integer(),      nullable=True),
        sa.Column("end_user_id",         sa.String(255),    nullable=True),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_events_chatbot_date", "analytics_events",
                    ["chatbot_id", "created_at"])
    op.create_index("idx_events_workspace_date", "analytics_events",
                    ["workspace_id", "created_at"])
    op.create_index("idx_events_type", "analytics_events", ["event_type"])

    # ── analytics_daily ───────────────────────────────────────────────────────
    op.create_table(
        "analytics_daily",
        sa.Column("id",              postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id",    postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chatbot_id",      postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("chatbots.id",   ondelete="CASCADE"), nullable=False),
        sa.Column("date",            sa.Date(), nullable=False),
        sa.Column("total_sessions",       sa.Integer(), server_default="0"),
        sa.Column("total_messages",       sa.Integer(), server_default="0"),
        sa.Column("unique_users",         sa.Integer(), server_default="0"),
        sa.Column("avg_confidence",       sa.Numeric(5, 2), nullable=True),
        sa.Column("avg_response_time_ms", sa.Integer(), nullable=True),
        sa.Column("total_tokens",         sa.Integer(), server_default="0"),
        sa.Column("clarification_rate",   sa.Numeric(5, 2), nullable=True),
        sa.Column("resolution_rate",      sa.Numeric(5, 2), nullable=True),
        sa.Column("total_cost_usd",       sa.Numeric(10, 4), server_default="0"),
        sa.Column("updated_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("workspace_id", "chatbot_id", "date",
                            name="uq_analytics_daily"),
    )
    op.create_index("idx_daily_chatbot_date", "analytics_daily",
                    ["chatbot_id", "date"])
    op.create_index("idx_daily_workspace_date", "analytics_daily",
                    ["workspace_id", "date"])

    # ── deployment_channels ───────────────────────────────────────────────────
    op.execute("DROP TABLE IF EXISTS deployment_channels CASCADE")
    op.create_table(
        "deployment_channels",
        sa.Column("id",           postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chatbot_id",   postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("chatbots.id",   ondelete="CASCADE"), nullable=False),
        sa.Column("channel_type", sa.String(50),  nullable=False),  # widget | api | slack | ...
        sa.Column("channel_name", sa.String(255), nullable=False),
        sa.Column("config",       postgresql.JSONB(), server_default="{}"),
        # Widget-specific
        sa.Column("allowed_domains", postgresql.JSONB(), server_default="[]"),
        # API key channel
        sa.Column("api_key_prefix", sa.String(20),  nullable=True),
        sa.Column("api_key_hash",   sa.String(255), nullable=True),
        sa.Column("is_active",  sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_deploy_chatbot",  "deployment_channels", ["chatbot_id"])
    op.create_index("idx_deploy_type",     "deployment_channels", ["channel_type"])

    # ── plans ─────────────────────────────────────────────────────────────────
    op.create_table(
        "plans",
        sa.Column("id",               postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name",             sa.String(100), nullable=False, unique=True),
        sa.Column("slug",             sa.String(50),  nullable=False, unique=True),
        sa.Column("price_monthly_usd", sa.Numeric(10, 2), nullable=False),
        sa.Column("price_yearly_usd",  sa.Numeric(10, 2), nullable=True),
        sa.Column("chatbot_limit",        sa.Integer(), server_default="3"),
        sa.Column("monthly_message_limit", sa.Integer(), server_default="5000"),
        sa.Column("storage_limit_mb",      sa.Integer(), server_default="100"),
        sa.Column("team_member_limit",     sa.Integer(), server_default="2"),
        sa.Column("features",   postgresql.JSONB(), server_default="[]"),
        sa.Column("is_active",  sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── subscriptions ─────────────────────────────────────────────────────────
    op.create_table(
        "subscriptions",
        sa.Column("id",           postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
                  nullable=False, unique=True),
        sa.Column("plan_id",      postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("plans.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status",          sa.String(50),  server_default="active"),
        # active | trialing | past_due | canceled | paused
        sa.Column("billing_cycle",   sa.String(20),  server_default="monthly"),
        # Stripe / payment gateway refs
        sa.Column("stripe_customer_id",     sa.String(255), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(255), nullable=True),
        sa.Column("current_period_start",   sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end",     sa.DateTime(timezone=True), nullable=True),
        sa.Column("trial_ends_at",          sa.DateTime(timezone=True), nullable=True),
        sa.Column("canceled_at",            sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_sub_workspace", "subscriptions", ["workspace_id"])
    op.create_index("idx_sub_stripe_cust", "subscriptions", ["stripe_customer_id"],
                    postgresql_where=sa.text("stripe_customer_id IS NOT NULL"))

    # ── invoices ──────────────────────────────────────────────────────────────
    op.execute("DROP TABLE IF EXISTS invoices CASCADE")
    op.create_table(
        "invoices",
        sa.Column("id",              postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id",    postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subscription_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("invoice_number",  sa.String(50), nullable=False, unique=True),
        sa.Column("status",    sa.String(50),   server_default="draft"),
        # draft | open | paid | void | uncollectible
        sa.Column("currency", sa.String(3),    server_default="USD"),
        sa.Column("subtotal_usd",    sa.Numeric(10, 2), server_default="0"),
        sa.Column("tax_usd",         sa.Numeric(10, 2), server_default="0"),
        sa.Column("total_usd",       sa.Numeric(10, 2), server_default="0"),
        sa.Column("period_start",    sa.Date(), nullable=False),
        sa.Column("period_end",      sa.Date(), nullable=False),
        sa.Column("stripe_invoice_id", sa.String(255), nullable=True),
        sa.Column("paid_at",   sa.DateTime(timezone=True), nullable=True),
        sa.Column("due_at",    sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_invoice_workspace", "invoices", ["workspace_id"])
    op.create_index("idx_invoice_status",    "invoices", ["status"])

    # ── invoice_line_items ────────────────────────────────────────────────────
    op.create_table(
        "invoice_line_items",
        sa.Column("id",         postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("description",  sa.Text(),          nullable=False),
        sa.Column("quantity",     sa.Integer(),        server_default="1"),
        sa.Column("unit_price",   sa.Numeric(10, 4),  nullable=False),
        sa.Column("amount_usd",   sa.Numeric(10, 2),  nullable=False),
        sa.Column("item_type",    sa.String(50),       server_default="subscription"),
        # subscription | overage_messages | overage_storage | add_on
        sa.Column("metadata_",    postgresql.JSONB(),  server_default="{}"),
    )
    op.create_index("idx_lineitems_invoice", "invoice_line_items", ["invoice_id"])


def downgrade() -> None:
    op.drop_table("invoice_line_items")
    op.drop_table("invoices")
    op.drop_table("subscriptions")
    op.drop_table("plans")
    op.drop_table("deployment_channels")
    op.drop_table("analytics_daily")
    op.drop_table("analytics_events")