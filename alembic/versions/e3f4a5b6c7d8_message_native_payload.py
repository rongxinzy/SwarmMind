"""Add native DeerFlow payload to messages.

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-06-26
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "e3f4a5b6c7d8"
down_revision = "d2e3f4a5b6c7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply native message payload column."""
    op.add_column("messages", sa.Column("native_payload", sa.JSON(), nullable=True))


def downgrade() -> None:
    """Drop native message payload column."""
    op.drop_column("messages", "native_payload")
