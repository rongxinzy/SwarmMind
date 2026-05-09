"""phase-c: conversation is_project_bound, team instance runtime_profile_id

Revision ID: a1b2c3d4e5f6
Revises: 5d7f6c8e9a10
Create Date: 2026-05-09 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "5d7f6c8e9a10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "conversations",
        sa.Column("is_project_bound", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "project_agent_team_instances",
        sa.Column("runtime_profile_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("conversations", "is_project_bound")
    op.drop_column("project_agent_team_instances", "runtime_profile_id")
