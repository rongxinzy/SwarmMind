"""Add project memberships

Revision ID: c1d2e3f4a5b6
Revises: b1c2d3e4f5a6
Create Date: 2026-05-17
"""

import sqlalchemy as sa

from alembic import op

revision = "c1d2e3f4a5b6"
down_revision = "b1c2d3e4f5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create project_memberships table."""
    op.create_table(
        "project_memberships",
        sa.Column("membership_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("member_id", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=True),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.project_id"]),
        sa.PrimaryKeyConstraint("membership_id"),
    )
    op.create_index("idx_project_memberships_project", "project_memberships", ["project_id"])
    op.create_index("idx_project_memberships_member", "project_memberships", ["member_id"])
    op.create_index("idx_project_memberships_role", "project_memberships", ["role"])
    op.create_index(
        "idx_project_memberships_project_member",
        "project_memberships",
        ["project_id", "member_id"],
        unique=True,
    )


def downgrade() -> None:
    """Drop project_memberships table."""
    op.drop_index("idx_project_memberships_project_member", table_name="project_memberships")
    op.drop_index("idx_project_memberships_role", table_name="project_memberships")
    op.drop_index("idx_project_memberships_member", table_name="project_memberships")
    op.drop_index("idx_project_memberships_project", table_name="project_memberships")
    op.drop_table("project_memberships")
