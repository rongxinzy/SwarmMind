"""add phase and risk_level to projects

Revision ID: k0h3f7i8l9m0
Revises: j9g2e6h5i7k8
Create Date: 2026-04-26 17:16:48.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'k0h3f7i8l9m0'
down_revision: Union[str, Sequence[str], None] = 'cc8de8a23de8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('projects', schema=None) as batch_op:
        batch_op.add_column(sa.Column('phase', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('risk_level', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('projects', schema=None) as batch_op:
        batch_op.drop_column('risk_level')
        batch_op.drop_column('phase')
