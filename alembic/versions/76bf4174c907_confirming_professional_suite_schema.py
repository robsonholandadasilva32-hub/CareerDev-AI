"""Confirming Professional Suite Schema

Revision ID: 76bf4174c907
Revises: a3783c542714
Create Date: 2026-01-27 18:12:17.403247

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '76bf4174c907'
down_revision: Union[str, Sequence[str], None] = 'a3783c542714'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Users - Add new auth tokens
    # Using batch_alter_table for SQLite compatibility (and cleaner syntax)
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('github_token', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('linkedin_token', sa.String(), nullable=True))

    # Career Profiles - Add new insights columns
    with op.batch_alter_table('career_profiles') as batch_op:
        batch_op.add_column(sa.Column('ai_insights_summary', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('skills_graph_data', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('github_activity_metrics', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('linkedin_alignment_data', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('career_profiles') as batch_op:
        batch_op.drop_column('linkedin_alignment_data')
        batch_op.drop_column('github_activity_metrics')
        batch_op.drop_column('skills_graph_data')
        batch_op.drop_column('ai_insights_summary')

    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('linkedin_token')
        batch_op.drop_column('github_token')
