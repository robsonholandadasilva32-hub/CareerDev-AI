"""purge_payment_columns

Revision ID: 1234567890ad
Revises: 1234567890ac
Create Date: 2024-05-22 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '1234567890ad'
down_revision = '1234567890ac'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Update existing users to be premium before dropping columns if logic depended on it,
    # but strictly we just want to ensure everyone is premium.
    op.execute("UPDATE users SET is_premium = 1")

    # Batch operations are needed for SQLite to drop columns
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('subscription_status')
        batch_op.drop_column('subscription_end_date')
        batch_op.drop_column('is_recurring')
        batch_op.drop_column('stripe_customer_id')
        batch_op.drop_column('billing_address_street')
        batch_op.drop_column('billing_address_number')
        batch_op.drop_column('billing_address_complement')
        batch_op.drop_column('billing_address_city')
        batch_op.drop_column('billing_address_state')
        batch_op.drop_column('billing_address_zip_code')
        batch_op.drop_column('billing_address_country')


def downgrade() -> None:
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('subscription_status', sa.String(), server_default="free"))
        batch_op.add_column(sa.Column('subscription_end_date', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('is_recurring', sa.Boolean(), server_default="0"))
        batch_op.add_column(sa.Column('stripe_customer_id', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('billing_address_street', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('billing_address_number', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('billing_address_complement', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('billing_address_city', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('billing_address_state', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('billing_address_zip_code', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('billing_address_country', sa.String(), nullable=True))
