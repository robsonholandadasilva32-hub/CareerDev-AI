"""seed_admin_user

Revision ID: a3783c542714
Revises: 4e3e9fe45afb
Create Date: 2026-01-24 22:49:53.370546

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3783c542714'
down_revision: Union[str, Sequence[str], None] = '4e3e9fe45afb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        UPDATE users
        SET is_admin = true
        WHERE email = 'robsonholandasilva@yahoo.com.br';
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("""
        UPDATE users
        SET is_admin = false
        WHERE email = 'robsonholandasilva@yahoo.com.br';
    """)
