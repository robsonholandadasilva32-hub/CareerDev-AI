"""Add governance_logs table

Revision ID: a50c295055d0
Revises: a294b06baf5d
Create Date: 2026-02-08 02:56:47.620395

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a50c295055d0'
down_revision: Union[str, Sequence[str], None] = 'a294b06baf5d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('governance_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=True),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_governance_logs_id'), 'governance_logs', ['id'], unique=False)
    op.create_index(op.f('ix_governance_logs_user_id'), 'governance_logs', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_governance_logs_user_id'), table_name='governance_logs')
    op.drop_index(op.f('ix_governance_logs_id'), table_name='governance_logs')
    op.drop_table('governance_logs')
