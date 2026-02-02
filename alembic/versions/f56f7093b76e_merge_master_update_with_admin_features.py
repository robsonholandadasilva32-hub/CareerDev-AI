"""merge master update with admin features

Revision ID: f56f7093b76e
Revises: 1234567890af, a3783c542714
Create Date: 2026-02-01 23:58:39.112741

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f56f7093b76e'
down_revision: Union[str, Sequence[str], None] = ('1234567890af', 'a3783c542714')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
