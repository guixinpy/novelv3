"""add dialog message types and meta

Revision ID: d9f5e6a1c2b3
Revises: bdab5f1bbbe7
Create Date: 2026-04-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d9f5e6a1c2b3"
down_revision: Union[str, None] = "bdab5f1bbbe7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "dialog_messages",
        sa.Column("message_type", sa.String(), nullable=False, server_default="text"),
    )
    op.add_column("dialog_messages", sa.Column("meta", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("dialog_messages", "meta")
    op.drop_column("dialog_messages", "message_type")
