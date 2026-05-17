"""Add local users and API tokens.

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-05-17
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "d2e3f4a5b6c7"
down_revision = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply users and tokens schema."""
    op.create_table(
        "users",
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=True),
        sa.Column("password_hash", sa.String(), nullable=True),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_index("idx_users_email", "users", ["email"], unique=True)
    op.create_index("idx_users_role", "users", ["role"], unique=False)
    op.create_index("idx_users_status", "users", ["status"], unique=False)

    op.create_table(
        "user_tokens",
        sa.Column("token_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"]),
        sa.PrimaryKeyConstraint("token_id"),
    )
    op.create_index("idx_user_tokens_hash", "user_tokens", ["token_hash"], unique=True)
    op.create_index("idx_user_tokens_status", "user_tokens", ["status"], unique=False)
    op.create_index("idx_user_tokens_user", "user_tokens", ["user_id"], unique=False)


def downgrade() -> None:
    """Drop users and tokens schema."""
    op.drop_index("idx_user_tokens_user", table_name="user_tokens")
    op.drop_index("idx_user_tokens_status", table_name="user_tokens")
    op.drop_index("idx_user_tokens_hash", table_name="user_tokens")
    op.drop_table("user_tokens")

    op.drop_index("idx_users_status", table_name="users")
    op.drop_index("idx_users_role", table_name="users")
    op.drop_index("idx_users_email", table_name="users")
    op.drop_table("users")
