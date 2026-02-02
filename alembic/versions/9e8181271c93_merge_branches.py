"""merge_branches

Revision ID: 9e8181271c93
Revises: a821c942f17f
Create Date: 2026-02-02 18:07:33.556887

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9e8181271c93'
down_revision: Union[str, Sequence[str], None] = 'a821c942f17f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
