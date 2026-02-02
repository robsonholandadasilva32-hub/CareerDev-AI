"""add last_weekly_check with timezone

Revision ID: h1234567890ai
Revises: g1234567890ah
Create Date: 2026-02-02 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import ProgrammingError, InternalError

# revision identifiers, used by Alembic.
revision = 'h1234567890ai'
down_revision = 'g1234567890ah'
branch_labels = None
depends_on = None

def upgrade():
    conn = op.get_bind()
    # Attempt to add the column with timezone=True
    try:
        with conn.begin_nested():
            op.add_column('users', sa.Column('last_weekly_check', sa.DateTime(timezone=True), nullable=True))
    except (ProgrammingError, InternalError) as e:
        print(f"Skipping add_column (likely exists): {e}")

def downgrade():
    try:
        op.drop_column('users', 'last_weekly_check')
    except (ProgrammingError, InternalError):
        pass
