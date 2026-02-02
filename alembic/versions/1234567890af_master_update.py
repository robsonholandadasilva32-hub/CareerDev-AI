"""master update: weekly routines and user check

Revision ID: 1234567890af
Revises: 1234567890ae
Create Date: 2024-10-28 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = '1234567890af'
down_revision = '1234567890ae'
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_context().bind
    insp = sa.inspect(bind)
    existing_tables = insp.get_table_names()
    existing_columns = [c['name'] for c in insp.get_columns('users')]

    # 1. Add last_weekly_check to users
    if 'last_weekly_check' not in existing_columns:
        op.add_column('users', sa.Column('last_weekly_check', sa.DateTime(), nullable=True))

    # 2. Create weekly_routines table
    if 'weekly_routines' not in existing_tables:
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
