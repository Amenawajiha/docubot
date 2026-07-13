"""phase 2 — workspace & chatbot CRUD (no schema changes)

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-30

All tables needed for Phase 2 (workspaces, workspace_members, chatbots)
were already created in migration 0001. This migration exists to mark
the phase boundary clearly in the migration history and to document that
no additional columns were required.

If future requirements add columns (e.g. workspace.avatar_url,
chatbot.webhook_url), add them here rather than modifying 0001.
"""

from collections.abc import Sequence

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass  # All Phase 2 tables exist from migration 0001


def downgrade() -> None:
    pass