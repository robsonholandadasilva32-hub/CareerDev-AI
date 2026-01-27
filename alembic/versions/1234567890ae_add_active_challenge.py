"""add active_challenge to career_profile

Revision ID: 1234567890ae
Revises: 1234567890ad
Create Date: 2024-05-25 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '1234567890ae'
down_revision = '1234567890ad'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('career_profiles') as batch_op:
        batch_op.add_column(sa.Column('active_challenge', sa.JSON(), nullable=True))

def downgrade():
    with op.batch_alter_table('career_profiles') as batch_op:
        batch_op.drop_column('active_challenge')
