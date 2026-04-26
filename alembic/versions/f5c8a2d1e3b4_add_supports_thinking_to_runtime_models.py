"""add supports_thinking to runtime_models

Revision ID: f5c8a2d1e3b4
Revises: e4e591a43be1
Create Date: 2026-04-26 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f5c8a2d1e3b4'
down_revision: Union[str, Sequence[str], None] = 'e4e591a43be1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('runtime_models', sa.Column('supports_thinking', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('runtime_models', 'supports_thinking')
