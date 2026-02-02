"""fix missing columns and tables

Revision ID: g1234567890ah
Revises: f56f7093b76e
Create Date: 2026-02-02 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import ProgrammingError, InternalError

# revision identifiers, used by Alembic.
revision = 'g1234567890ah'
down_revision = 'f56f7093b76e'
branch_labels = None
depends_on = None

def safe_add_column(table_name, column):
    """
    Idempotently add a column to a table.
    """
    bind = op.get_context().bind
    try:
        with bind.begin_nested():
            op.add_column(table_name, column)
    except (ProgrammingError, InternalError):
        # Column likely already exists
        pass

def safe_create_table(table_name, *columns, **kwargs):
    """
    Idempotently create a table.
    """
    bind = op.get_context().bind
    try:
        with bind.begin_nested():
            op.create_table(table_name, *columns, **kwargs)
            # If the table creation succeeds, we should also try to create the index if it was part of the original logic
            if table_name == 'weekly_routines':
                 op.create_index(op.f('ix_weekly_routines_user_id'), 'weekly_routines', ['user_id'], unique=False)
    except (ProgrammingError, InternalError):
        # Table likely already exists
        pass

def upgrade():
    # --- Users Table Columns ---

    # Address fields
    safe_add_column('users', sa.Column('address_street', sa.String(), nullable=True))
    safe_add_column('users', sa.Column('address_number', sa.String(), nullable=True))
    safe_add_column('users', sa.Column('address_complement', sa.String(), nullable=True))
    safe_add_column('users', sa.Column('address_city', sa.String(), nullable=True))
    safe_add_column('users', sa.Column('address_state', sa.String(), nullable=True))
    safe_add_column('users', sa.Column('address_zip_code', sa.String(), nullable=True))
    safe_add_column('users', sa.Column('address_country', sa.String(), nullable=True))

    # Billing address fields
    safe_add_column('users', sa.Column('billing_address_street', sa.String(), nullable=True))
    safe_add_column('users', sa.Column('billing_address_number', sa.String(), nullable=True))
    safe_add_column('users', sa.Column('billing_address_complement', sa.String(), nullable=True))
    safe_add_column('users', sa.Column('billing_address_city', sa.String(), nullable=True))
    safe_add_column('users', sa.Column('billing_address_state', sa.String(), nullable=True))
    safe_add_column('users', sa.Column('billing_address_zip_code', sa.String(), nullable=True))
    safe_add_column('users', sa.Column('billing_address_country', sa.String(), nullable=True))

    # Profile status fields
    safe_add_column('users', sa.Column('is_profile_completed', sa.Boolean(), server_default=sa.false()))
    safe_add_column('users', sa.Column('terms_accepted', sa.Boolean(), server_default=sa.false()))
    safe_add_column('users', sa.Column('terms_accepted_at', sa.DateTime(), nullable=True))

    # Last weekly check
    safe_add_column('users', sa.Column('last_weekly_check', sa.DateTime(), nullable=True))

    # --- Weekly Routines Table ---
    safe_create_table('weekly_routines',
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

    # Note: Index creation is handled inside safe_create_table to keep it atomic with table creation
    # or skipped if table exists. If table exists but index doesn't, this simple logic might skip index.
    # But for this 'fix' scenario where we assume total failure or success of the previous migration block,
    # this is acceptable. If we wanted to be more granular, we would check index separately.
    # Given the previous migration created table AND index in one block (conceptually), checking table existence is a good proxy.
    # However, to be extra safe, let's try to create the index separately too if the table check passes or fails.
    # But `safe_create_table` eats the exception.
    # Let's refine `safe_create_table` or just call `safe_create_index` separately?
    # Simpler: The previous migration (1234567890af) did:
    #   create_table
    #   create_index
    # If create_table failed (because it exists), we might still want to ensure the index exists.
    # Let's add a explicit safe_create_index check.

    try:
        bind = op.get_context().bind
        with bind.begin_nested():
            op.create_index(op.f('ix_weekly_routines_user_id'), 'weekly_routines', ['user_id'], unique=False)
    except (ProgrammingError, InternalError):
        pass


def downgrade():
    # We attempt to drop everything we might have added.
    # This is standard, though in a "fix" scenario, running downgrade might leave us in the broken state we started with.

    bind = op.get_context().bind

    # Drop index and table
    try:
        with bind.begin_nested():
            op.drop_index(op.f('ix_weekly_routines_user_id'), table_name='weekly_routines')
            op.drop_table('weekly_routines')
    except (ProgrammingError, InternalError):
        pass

    # Drop columns
    columns_to_drop = [
        'address_street', 'address_number', 'address_complement', 'address_city',
        'address_state', 'address_zip_code', 'address_country',
        'billing_address_street', 'billing_address_number', 'billing_address_complement',
        'billing_address_city', 'billing_address_state', 'billing_address_zip_code',
        'billing_address_country',
        'is_profile_completed', 'terms_accepted', 'terms_accepted_at',
        'last_weekly_check'
    ]

    for col in columns_to_drop:
        try:
            with bind.begin_nested():
                op.drop_column('users', col)
        except (ProgrammingError, InternalError):
            pass
