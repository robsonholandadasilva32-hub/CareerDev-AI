"""Add GovernanceLog and MLRiskLog

Revision ID: c529f12a3e5b
Revises: a294b06baf5d
Create Date: 2026-02-14 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision: str = 'c529f12a3e5b'
down_revision: Union[str, Sequence[str], None] = 'a294b06baf5d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create governance_logs table
    op.create_table('governance_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('severity', sa.String(), nullable=True, server_default='INFO'),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_governance_logs_id'), 'governance_logs', ['id'], unique=False)

    # Create ml_risk_logs table
    op.create_table('ml_risk_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('ml_risk', sa.Integer(), nullable=True),
        sa.Column('rule_risk', sa.Integer(), nullable=True),
        sa.Column('final_risk', sa.Integer(), nullable=True),
        sa.Column('model_version', sa.String(length=20), nullable=True),
        sa.Column('experiment_group', sa.String(length=10), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('ml_risk_logs')
    op.drop_index(op.f('ix_governance_logs_id'), table_name='governance_logs')
    op.drop_table('governance_logs')
