"""add artifacts table

Revision ID: g6d9b3e2f4c5
Revises: f5c8a2d1e3b4
Create Date: 2026-04-26 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'g6d9b3e2f4c5'
down_revision: Union[str, Sequence[str], None] = 'f5c8a2d1e3b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('artifacts',
        sa.Column('artifact_id', sa.String(), nullable=False),
        sa.Column('conversation_id', sa.String(), nullable=False),
        sa.Column('message_id', sa.String(), nullable=True),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('artifact_type', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id'], ),
        sa.PrimaryKeyConstraint('artifact_id')
    )
    op.create_index('idx_artifacts_conversation', 'artifacts', ['conversation_id'], unique=False)
    op.create_index('idx_artifacts_message', 'artifacts', ['message_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_artifacts_message', table_name='artifacts')
    op.drop_index('idx_artifacts_conversation', table_name='artifacts')
    op.drop_table('artifacts')
