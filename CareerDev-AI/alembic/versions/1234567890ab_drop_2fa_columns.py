"""drop 2fa columns

Revision ID: 1234567890ab
Revises:
Create Date: 2024-05-22 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = '1234567890ab'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)

    # DROP columns from 'users'
    # We check existing columns to avoid errors if they are already gone
    try:
        existing_columns = [c['name'] for c in inspector.get_columns('users')]
    except sa.exc.NoSuchTableError:
        # If users table doesn't exist, we can't drop columns.
        # This might happen in a fresh init if create_all hasn't run yet.
        return

    columns_to_drop = [
        'two_factor_secret',
        'is_2fa_enabled',
        'backup_codes',
        'two_factor_method',
        'two_factor_enabled'
    ]

    with op.batch_alter_table('users') as batch_op:
        for col in columns_to_drop:
            if col in existing_columns:
                batch_op.drop_column(col)

    # DROP table 'otps'
    existing_tables = inspector.get_table_names()
    if 'otps' in existing_tables:
        op.drop_table('otps')

def downgrade():
    # Re-add columns to 'users'
    # This is a best-effort recreation for rollback
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('two_factor_secret', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('is_2fa_enabled', sa.Boolean(), default=False))
        batch_op.add_column(sa.Column('backup_codes', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('two_factor_method', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('two_factor_enabled', sa.Boolean(), default=False))

    # Re-create table 'otps'
    op.create_table(
        'otps',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('code', sa.String(), nullable=False),
        sa.Column('method', sa.String(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now())
    )
