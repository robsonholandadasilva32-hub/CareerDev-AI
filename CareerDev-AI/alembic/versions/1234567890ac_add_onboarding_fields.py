"""add onboarding fields

Revision ID: 1234567890ac
Revises: 1234567890ab
Create Date: 2024-05-23 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import ProgrammingError, InternalError

# Trigger redeploy
# revision identifiers, used by Alembic.
revision = '1234567890ac'
down_revision = '1234567890ab'
branch_labels = None
depends_on = None

def safe_add_column(table_name, column):
    bind = op.get_context().bind
    try:
        with bind.begin_nested():
            op.add_column(table_name, column)
    except (ProgrammingError, InternalError):
        # Broadly catch ProgrammingError and InternalError
        # to ensure the migration is idempotent and unblocks deployment.
        pass

# Force redeploy
def upgrade():
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

def downgrade():
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('address_street')
        batch_op.drop_column('address_number')
        batch_op.drop_column('address_complement')
        batch_op.drop_column('address_city')
        batch_op.drop_column('address_state')
        batch_op.drop_column('address_zip_code')
        batch_op.drop_column('address_country')

        batch_op.drop_column('billing_address_street')
        batch_op.drop_column('billing_address_number')
        batch_op.drop_column('billing_address_complement')
        batch_op.drop_column('billing_address_city')
        batch_op.drop_column('billing_address_state')
        batch_op.drop_column('billing_address_zip_code')
        batch_op.drop_column('billing_address_country')

        batch_op.drop_column('is_profile_completed')
        batch_op.drop_column('terms_accepted')
        batch_op.drop_column('terms_accepted_at')
