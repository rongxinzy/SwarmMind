"""make_run_conversation_id_nullable

Revision ID: 363a02897c48
Revises: 8f27dafa0bbc
Create Date: 2026-04-26 17:16:48.576319

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '363a02897c48'
down_revision: Union[str, Sequence[str], None] = '8f27dafa0bbc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: make runs.conversation_id nullable."""
    with op.batch_alter_table('runs', schema=None) as batch_op:
        batch_op.alter_column(
            'conversation_id',
            existing_type=sa.VARCHAR(),
            nullable=True,
        )


def downgrade() -> None:
    """Downgrade schema: make runs.conversation_id non-nullable."""
    with op.batch_alter_table('runs', schema=None) as batch_op:
        batch_op.alter_column(
            'conversation_id',
            existing_type=sa.VARCHAR(),
            nullable=False,
        )
