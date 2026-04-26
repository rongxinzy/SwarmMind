"""add runs table

Revision ID: h7e0c4f3g5d6
Revises: g6d9b3e2f4c5
Create Date: 2026-04-26 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'h7e0c4f3g5d6'
down_revision: Union[str, Sequence[str], None] = 'g6d9b3e2f4c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('runs',
        sa.Column('run_id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), nullable=True),
        sa.Column('conversation_id', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('goal', sa.String(), nullable=True),
        sa.Column('summary', sa.String(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.project_id'], ),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ),
        sa.PrimaryKeyConstraint('run_id')
    )
    op.create_index('idx_runs_project', 'runs', ['project_id'], unique=False)
    op.create_index('idx_runs_conversation', 'runs', ['conversation_id'], unique=False)
    op.create_index('idx_runs_status', 'runs', ['status'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_runs_status', table_name='runs')
    op.drop_index('idx_runs_conversation', table_name='runs')
    op.drop_index('idx_runs_project', table_name='runs')
    op.drop_table('runs')
