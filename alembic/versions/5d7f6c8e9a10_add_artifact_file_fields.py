"""add artifact file fields

Revision ID: 5d7f6c8e9a10
Revises: 09cafc3a6469
Create Date: 2026-05-05 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5d7f6c8e9a10"
down_revision: str | Sequence[str] | None = "09cafc3a6469"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("artifacts", sa.Column("path", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column("artifacts", sa.Column("storage_uri", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column("artifacts", sa.Column("mime_type", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column("artifacts", sa.Column("size_bytes", sa.Integer(), nullable=True))
    op.create_index("idx_artifacts_path", "artifacts", ["path"], unique=False)
    op.execute(
        "UPDATE artifacts "
        "SET path = name "
        "WHERE path IS NULL "
        "AND (name LIKE '/mnt/user-data/%' OR name LIKE 'mnt/user-data/%')"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_artifacts_path", table_name="artifacts")
    op.drop_column("artifacts", "size_bytes")
    op.drop_column("artifacts", "mime_type")
    op.drop_column("artifacts", "storage_uri")
    op.drop_column("artifacts", "path")
