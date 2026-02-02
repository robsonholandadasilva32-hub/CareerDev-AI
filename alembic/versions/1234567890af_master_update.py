"""master update: weekly routines and user check

Revision ID: 1234567890af
Revises: 1234567890ae
Create Date: 2024-10-28 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '1234567890af'
down_revision = '1234567890ae'
branch_labels = None
depends_on = None

def upgrade():
    # 1. Add last_weekly_check to users
    op.add_column('users', sa.Column('last_weekly_check', sa.DateTime(), nullable=True))

    # 2. Create weekly_routines table
    # Check if table exists first to be safe, or just create it.
    # Standard alembic just creates. We assume it doesn't exist or we accept error if manual sync issues.
    # Given the instructions "Create the table", I will create it.
    op.create_table('weekly_routines',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('week_id', sa.String(length=10), nullable=False),
        sa.Column('mode', sa.String(length=20), nullable=True),
        sa.Column('focus', sa.String(length=50), nullable=False),
        sa.Column('tasks', sa.JSON(), nullable=False),
        sa.Column('suggested_pr', sa.JSON(), nullable=True),
        sa.Column('completed', sa.Boolean(), nullable=True),
        sa.Column('completion_rate', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    # Add index for faster lookups by user and week
    op.create_index(op.f('ix_weekly_routines_user_id'), 'weekly_routines', ['user_id'], unique=False)

def downgrade():
    op.drop_index(op.f('ix_weekly_routines_user_id'), table_name='weekly_routines')
    op.drop_table('weekly_routines')
    op.drop_column('users', 'last_weekly_check')
