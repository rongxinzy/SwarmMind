"""add tasks table

Revision ID: i8f1d5g4h6e7
Revises: h7e0c4f3g5d6
Create Date: 2026-04-26 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'i8f1d5g4h6e7'
down_revision: Union[str, Sequence[str], None] = '363a02897c48'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('tasks',
        sa.Column('task_id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), nullable=False),
        sa.Column('run_id', sa.String(), nullable=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('assignee_role', sa.String(), nullable=True),
        sa.Column('source_workstream', sa.String(), nullable=True),
        sa.Column('artifact_ids', sa.JSON(), nullable=True),
        sa.Column('priority', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.project_id'], ),
        sa.ForeignKeyConstraint(['run_id'], ['runs.run_id'], ),
        sa.PrimaryKeyConstraint('task_id')
    )
    op.create_index('idx_tasks_project', 'tasks', ['project_id'], unique=False)
    op.create_index('idx_tasks_status', 'tasks', ['status'], unique=False)
    op.create_index('idx_tasks_run', 'tasks', ['run_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_tasks_run', table_name='tasks')
    op.drop_index('idx_tasks_status', table_name='tasks')
    op.drop_index('idx_tasks_project', table_name='tasks')
    op.drop_table('tasks')
