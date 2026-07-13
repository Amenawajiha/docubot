"""
add oauth columns to users
Revision ID: 002
Revises: 0001
Create Date: 2026-04-22
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision: str | None = "0001"
branch_labels: Sequence[str] | None = None
depends_on: str | Sequence[str] = None

def upgrade() -> None:
    op.add_column("users", sa.Column("oauth_provider", sa.String(), nullable=True))
    op.add_column("users", sa.Column("oauth_provider_id", sa.String(), nullable=True))
    op.add_column("users", sa.Column("avatar_url", sa.Text(), nullable=True))
    op.alter_column("users", "password_hash", nullable=True)

    op.create_index(
        "idx_users_oauth",
        "users",
        ["oauth_provider", "oauth_provider_id"],
        postgresql_where=sa.text("oauth_provider IS NOT NULL"),
    )

def downgrade() -> None:
    op.drop_index("idx_users_oauth", table_name="users")
    op.drop_column("users", "oauth_provider_id")
    op.drop_column("users", "oauth_provider")
    op.drop_column("users", "avatar_url")
    op.alter_column("users", "password_hash", nullable=False)
