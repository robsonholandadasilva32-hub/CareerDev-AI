"""merge conflicting heads

Revision ID: b759033bec88
Revises: 03fad1d840ed, h1234567890ai
Create Date: 2026-02-02 21:32:07.701715

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b759033bec88'
down_revision: Union[str, Sequence[str], None] = ('03fad1d840ed', 'h1234567890ai')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
