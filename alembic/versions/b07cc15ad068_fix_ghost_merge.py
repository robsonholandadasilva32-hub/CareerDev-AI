"""fix_ghost_merge

Revision ID: b07cc15ad068
Revises: 9e8181271c93
Create Date: 2026-02-02 18:12:58.876379

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b07cc15ad068'
down_revision: Union[str, Sequence[str], None] = '9e8181271c93'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
