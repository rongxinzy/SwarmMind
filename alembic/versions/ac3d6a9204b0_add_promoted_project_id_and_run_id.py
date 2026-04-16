"""add promoted_project_id and run_id

Revision ID: ac3d6a9204b0
Revises: 8c4f96c8f27a
Create Date: 2026-04-16 12:00:56.692935

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision: str = 'ac3d6a9204b0'
down_revision: Union[str, Sequence[str], None] = '8c4f96c8f27a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('conversations', sa.Column('promoted_project_id', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column('messages', sa.Column('run_id', sqlmodel.sql.sqltypes.AutoString(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('messages', 'run_id')
    op.drop_column('conversations', 'promoted_project_id')
