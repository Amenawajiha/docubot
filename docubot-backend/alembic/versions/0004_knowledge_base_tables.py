"""knowledge base tables — documents, ingestion_jobs, document_chunks, chatbot_collections

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-01

Four new tables that together track the full lifecycle of a document
from upload → ingestion → vector storage → deletion.

chatbot_documents      — one row per uploaded file (metadata + status)
ingestion_jobs         — one row per Celery ingestion task
document_chunks        — one row per text chunk produced from a document
chatbot_collections    — one row per chatbot's Qdrant collection (stats cache)
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:

    # ── chatbot_documents ─────────────────────────────────────────────────────
    # NOTE: Indexes are defined in the ORM model's __table_args__, so they're
    # auto-created when the table is created. Don't create them manually here.
    op.create_table(
        "chatbot_documents",
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
        # File identity
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("original_filename", sa.String(500), nullable=False),
        sa.Column("file_type", sa.String(50), nullable=False),   # pdf|docx|xlsx|txt|…
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        # S3/MinIO storage path
        sa.Column("storage_key", sa.Text(), nullable=True),      # set after upload
        # Processing state
        sa.Column(
            "upload_status",
            sa.String(50),
            server_default="pending",
            nullable=False,
        ),  # pending|uploaded|processing|completed|failed|deleted
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("chunk_count", sa.Integer(), server_default="0"),
        # Timestamps
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── ingestion_jobs ────────────────────────────────────────────────────────
    # NOTE: Indexes are defined in the ORM model's __table_args__, so they're
    # auto-created when the table is created. Don't create them manually here.
    op.create_table(
        "ingestion_jobs",
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
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chatbot_documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Celery task tracking
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column(
            "job_status",
            sa.String(50),
            server_default="queued",
            nullable=False,
        ),  # queued|validating|parsing|chunking|embedding|upserting|completed|failed
        sa.Column("progress_percent", sa.Integer(), server_default="0"),
        sa.Column("chunks_created", sa.Integer(), server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        # Timing
        sa.Column("queued_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── document_chunks ───────────────────────────────────────────────────────
    # NOTE: Indexes are defined in the ORM model's __table_args__, so they're
    # auto-created when the table is created. Don't create them manually here.
    op.create_table(
        "document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chatbot_documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
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
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text_content", sa.Text(), nullable=False),
        # Qdrant reference
        sa.Column("qdrant_point_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("qdrant_collection_name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── chatbot_collections ───────────────────────────────────────────────────
    # One row per chatbot's Qdrant collection. Acts as both a registry
    # and a denormalised stats cache (counts are updated after each job).
    # NOTE: Indexes are defined in the ORM model's __table_args__, so they're
    # auto-created when the table is created. Don't create them manually here.
    op.create_table(
        "chatbot_collections",
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
            primary_key=True,   # one collection per chatbot
        ),
        sa.Column("qdrant_collection_name", sa.String(255), nullable=False, unique=True),
        sa.Column("total_documents", sa.Integer(), server_default="0"),
        sa.Column("total_chunks", sa.Integer(), server_default="0"),
        sa.Column("storage_used_bytes", sa.BigInteger(), server_default="0"),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("document_chunks")
    op.drop_table("ingestion_jobs")
    op.drop_table("chatbot_collections")
    op.drop_table("chatbot_documents")