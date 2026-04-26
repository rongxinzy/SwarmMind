"""add fallback_model_names to llm_provider_models

Revision ID: e1f0a2b3c4d5
Revises: dcebeeadaefe
Create Date: 2026-04-26 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1f0a2b3c4d5'
down_revision: Union[str, Sequence[str], None] = 'dcebeeadaefe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('llm_provider_models', sa.Column('fallback_model_names', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('llm_provider_models', 'fallback_model_names')
