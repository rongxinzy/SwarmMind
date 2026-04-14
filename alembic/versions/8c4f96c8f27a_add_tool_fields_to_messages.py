"""add tool_call_id and name to messages

Revision ID: 8c4f96c8f27a
Revises: 1a3eb1e28e8d
Create Date: 2026-04-14 20:05:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8c4f96c8f27a"
down_revision: Union[str, Sequence[str], None] = "1a3eb1e28e8d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _get_message_columns() -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {column["name"] for column in inspector.get_columns("messages")}


def upgrade() -> None:
    """Upgrade schema."""
    columns = _get_message_columns()
    if "tool_call_id" not in columns:
        op.add_column("messages", sa.Column("tool_call_id", sa.String(), nullable=True))
    if "name" not in columns:
        op.add_column("messages", sa.Column("name", sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    columns = _get_message_columns()
    if "name" in columns:
        op.drop_column("messages", "name")
    if "tool_call_id" in columns:
        op.drop_column("messages", "tool_call_id")
