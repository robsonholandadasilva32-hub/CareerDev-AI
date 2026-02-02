"""add onboarding fields

Revision ID: 1234567890ac
Revises: 1234567890ab
Create Date: 2024-05-23 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = '1234567890ac'
down_revision = '1234567890ab'
branch_labels = None
depends_on = None

def upgrade():
    # Get database connection and inspector
    bind = op.get_context().bind
    insp = sa.inspect(bind)
    existing_columns = [c['name'] for c in insp.get_columns('users')]

    with op.batch_alter_table('users') as batch_op:
        # Address fields
        if 'address_street' not in existing_columns:
            batch_op.add_column(sa.Column('address_street', sa.String(), nullable=True))
        if 'address_number' not in existing_columns:
            batch_op.add_column(sa.Column('address_number', sa.String(), nullable=True))
        if 'address_complement' not in existing_columns:
            batch_op.add_column(sa.Column('address_complement', sa.String(), nullable=True))
        if 'address_city' not in existing_columns:
            batch_op.add_column(sa.Column('address_city', sa.String(), nullable=True))
        if 'address_state' not in existing_columns:
            batch_op.add_column(sa.Column('address_state', sa.String(), nullable=True))
        if 'address_zip_code' not in existing_columns:
            batch_op.add_column(sa.Column('address_zip_code', sa.String(), nullable=True))
        if 'address_country' not in existing_columns:
            batch_op.add_column(sa.Column('address_country', sa.String(), nullable=True))

        # Billing address fields
        if 'billing_address_street' not in existing_columns:
            batch_op.add_column(sa.Column('billing_address_street', sa.String(), nullable=True))
        if 'billing_address_number' not in existing_columns:
            batch_op.add_column(sa.Column('billing_address_number', sa.String(), nullable=True))
        if 'billing_address_complement' not in existing_columns:
            batch_op.add_column(sa.Column('billing_address_complement', sa.String(), nullable=True))
        if 'billing_address_city' not in existing_columns:
            batch_op.add_column(sa.Column('billing_address_city', sa.String(), nullable=True))
        if 'billing_address_state' not in existing_columns:
            batch_op.add_column(sa.Column('billing_address_state', sa.String(), nullable=True))
        if 'billing_address_zip_code' not in existing_columns:
            batch_op.add_column(sa.Column('billing_address_zip_code', sa.String(), nullable=True))
        if 'billing_address_country' not in existing_columns:
            batch_op.add_column(sa.Column('billing_address_country', sa.String(), nullable=True))

        # Profile status fields
        if 'is_profile_completed' not in existing_columns:
            batch_op.add_column(sa.Column('is_profile_completed', sa.Boolean(), server_default='0'))
        if 'terms_accepted' not in existing_columns:
            batch_op.add_column(sa.Column('terms_accepted', sa.Boolean(), server_default='0'))
        if 'terms_accepted_at' not in existing_columns:
            batch_op.add_column(sa.Column('terms_accepted_at', sa.DateTime(), nullable=True))

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
