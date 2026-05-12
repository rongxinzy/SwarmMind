"""Add step_key and source_event_at to tasks

Revision ID: b1c2d3e4f5a6
Revises: a1b2c3d4e5f6
Create Date: 2026-05-12
"""

import sqlalchemy as sa

from alembic import op

revision = "b1c2d3e4f5a6"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add step_key and source_event_at columns to tasks table."""
    op.add_column("tasks", sa.Column("step_key", sa.String(), nullable=True))
    op.add_column("tasks", sa.Column("source_event_at", sa.DateTime(), nullable=True))
    op.create_index("idx_tasks_step_key", "tasks", ["step_key"])
    # Note: SQLite doesn't support partial unique indexes; use a regular index
    op.create_index("idx_tasks_run_step", "tasks", ["run_id", "step_key"], unique=False)


def downgrade() -> None:
    """Remove step_key and source_event_at columns from tasks table."""
    op.drop_index("idx_tasks_run_step", table_name="tasks")
    op.drop_index("idx_tasks_step_key", table_name="tasks")
    op.drop_column("tasks", "source_event_at")
    op.drop_column("tasks", "step_key")
