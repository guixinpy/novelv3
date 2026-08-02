"""add dialog_type to dialogs

Revision ID: bfe0f1ff2e2d
Revises: f7c1e2d3a4b5
Create Date: 2026-04-22 13:26:16.528881

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bfe0f1ff2e2d'
down_revision: Union[str, None] = 'f7c1e2d3a4b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('dialogs', sa.Column('dialog_type', sa.String(), server_default='hermes', nullable=False))


def downgrade() -> None:
    op.drop_column('dialogs', 'dialog_type')
