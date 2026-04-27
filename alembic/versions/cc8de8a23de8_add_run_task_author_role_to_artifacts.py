"""add run_id, task_id, author_role to artifacts

Revision ID: cc8de8a23de8
Revises: j9g2e6h5i7k8
Create Date: 2026-04-26 17:16:48.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cc8de8a23de8'
down_revision: Union[str, Sequence[str], None] = 'j9g2e6h5i7k8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('artifacts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('run_id', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('task_id', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('author_role', sa.String(), nullable=True))
        batch_op.create_index('idx_artifacts_run', ['run_id'], unique=False)
        batch_op.create_index('idx_artifacts_task', ['task_id'], unique=False)
        batch_op.create_foreign_key('fk_artifacts_run_id', 'runs', ['run_id'], ['run_id'])
        batch_op.create_foreign_key('fk_artifacts_task_id', 'tasks', ['task_id'], ['task_id'])


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('artifacts', schema=None) as batch_op:
        batch_op.drop_constraint('fk_artifacts_task_id', type_='foreignkey')
        batch_op.drop_constraint('fk_artifacts_run_id', type_='foreignkey')
        batch_op.drop_index('idx_artifacts_task')
        batch_op.drop_index('idx_artifacts_run')
        batch_op.drop_column('author_role')
        batch_op.drop_column('task_id')
        batch_op.drop_column('run_id')
