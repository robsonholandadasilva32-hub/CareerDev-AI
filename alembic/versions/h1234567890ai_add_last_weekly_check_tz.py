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
    # Ensure last_weekly_check has timezone=True.
    # We attempt to ALTER first (expecting column from g1234567890ah).
    # If that fails (e.g. column missing), we ADD it.
    conn = op.get_bind()
    try:
        # Use a savepoint to ensure we can recover if alter fails (Postgres requirement)
        with conn.begin_nested():
            op.alter_column('users', 'last_weekly_check',
                            type_=sa.DateTime(timezone=True),
                            existing_type=sa.DateTime(timezone=False),
                            nullable=True)
    except (ProgrammingError, InternalError) as e:
        print(f"Alter failed (column likely missing), attempting to ADD: {e}")
        # If alter failed, we assume it's because the column is missing.
        # We try to add it. If THIS fails, we let it crash (no try/except).
        op.add_column('users', sa.Column('last_weekly_check', sa.DateTime(timezone=True), nullable=True))

def downgrade():
    # Revert to DateTime without timezone (matching state from g1234567890ah).
    op.alter_column('users', 'last_weekly_check',
                    type_=sa.DateTime(timezone=False),
                    existing_type=sa.DateTime(timezone=True),
                    nullable=True)
