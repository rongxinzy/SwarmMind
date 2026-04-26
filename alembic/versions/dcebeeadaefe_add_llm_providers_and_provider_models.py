"""add llm providers and provider models

Revision ID: dcebeeadaefe
Revises: h7e0c4f3g5d6
Create Date: 2026-04-26 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dcebeeadaefe'
down_revision: Union[str, Sequence[str], None] = 'h7e0c4f3g5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'llm_providers',
        sa.Column('provider_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('provider_type', sa.String(), nullable=False),
        sa.Column('api_key_encrypted', sa.String(), nullable=False),
        sa.Column('base_url', sa.String(), nullable=True),
        sa.Column('is_enabled', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_default', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('provider_id'),
    )
    op.create_index('idx_llm_providers_enabled', 'llm_providers', ['is_enabled'], unique=False)
    op.create_index('idx_llm_providers_default', 'llm_providers', ['is_default'], unique=False)

    op.create_table(
        'llm_provider_models',
        sa.Column('provider_id', sa.String(), nullable=False),
        sa.Column('model_name', sa.String(), nullable=False),
        sa.Column('litellm_model', sa.String(), nullable=False),
        sa.Column('display_name', sa.String(), nullable=True),
        sa.Column('supports_vision', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('supports_thinking', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_enabled', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['provider_id'], ['llm_providers.provider_id']),
        sa.PrimaryKeyConstraint('provider_id', 'model_name'),
    )
    op.create_index('idx_llm_provider_models_provider', 'llm_provider_models', ['provider_id'], unique=False)
    op.create_index('idx_llm_provider_models_enabled', 'llm_provider_models', ['is_enabled'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_llm_provider_models_enabled', table_name='llm_provider_models')
    op.drop_index('idx_llm_provider_models_provider', table_name='llm_provider_models')
    op.drop_table('llm_provider_models')
    op.drop_index('idx_llm_providers_default', table_name='llm_providers')
    op.drop_index('idx_llm_providers_enabled', table_name='llm_providers')
    op.drop_table('llm_providers')
