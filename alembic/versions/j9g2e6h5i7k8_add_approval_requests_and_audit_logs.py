"""add approval requests and audit logs

Revision ID: j9g2e6h5i7k8
Revises: i8f1d5g4h6e7
Create Date: 2026-04-26 17:16:48.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'j9g2e6h5i7k8'
down_revision: Union[str, Sequence[str], None] = 'i8f1d5g4h6e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('approval_requests',
        sa.Column('approval_id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), nullable=False),
        sa.Column('run_id', sa.String(), nullable=True),
        sa.Column('action_proposal_id', sa.String(), nullable=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('risk_tier', sa.String(), nullable=False),
        sa.Column('requested_capability', sa.String(), nullable=True),
        sa.Column('evidence', sa.String(), nullable=True),
        sa.Column('impact', sa.String(), nullable=True),
        sa.Column('approver_role', sa.String(), nullable=True),
        sa.Column('recovery_behavior', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('decision_reason', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.project_id'], ),
        sa.ForeignKeyConstraint(['run_id'], ['runs.run_id'], ),
        sa.ForeignKeyConstraint(['action_proposal_id'], ['action_proposals.id'], ),
        sa.PrimaryKeyConstraint('approval_id')
    )
    op.create_index('idx_approval_requests_project', 'approval_requests', ['project_id'], unique=False)
    op.create_index('idx_approval_requests_run', 'approval_requests', ['run_id'], unique=False)
    op.create_index('idx_approval_requests_status', 'approval_requests', ['status'], unique=False)
    op.create_index('idx_approval_requests_risk', 'approval_requests', ['risk_tier'], unique=False)

    op.create_table('audit_logs',
        sa.Column('audit_id', sa.String(), nullable=False),
        sa.Column('audit_type', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), nullable=False),
        sa.Column('run_id', sa.String(), nullable=True),
        sa.Column('approval_id', sa.String(), nullable=True),
        sa.Column('actor_id', sa.String(), nullable=True),
        sa.Column('actor_type', sa.String(), nullable=False),
        sa.Column('decision', sa.String(), nullable=True),
        sa.Column('reason', sa.String(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.project_id'], ),
        sa.ForeignKeyConstraint(['run_id'], ['runs.run_id'], ),
        sa.ForeignKeyConstraint(['approval_id'], ['approval_requests.approval_id'], ),
        sa.PrimaryKeyConstraint('audit_id')
    )
    op.create_index('idx_audit_logs_project', 'audit_logs', ['project_id'], unique=False)
    op.create_index('idx_audit_logs_run', 'audit_logs', ['run_id'], unique=False)
    op.create_index('idx_audit_logs_approval', 'audit_logs', ['approval_id'], unique=False)
    op.create_index('idx_audit_logs_timestamp', 'audit_logs', ['timestamp'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_audit_logs_timestamp', table_name='audit_logs')
    op.drop_index('idx_audit_logs_approval', table_name='audit_logs')
    op.drop_index('idx_audit_logs_run', table_name='audit_logs')
    op.drop_index('idx_audit_logs_project', table_name='audit_logs')
    op.drop_table('audit_logs')
    op.drop_index('idx_approval_requests_risk', table_name='approval_requests')
    op.drop_index('idx_approval_requests_status', table_name='approval_requests')
    op.drop_index('idx_approval_requests_run', table_name='approval_requests')
    op.drop_index('idx_approval_requests_project', table_name='approval_requests')
    op.drop_table('approval_requests')
