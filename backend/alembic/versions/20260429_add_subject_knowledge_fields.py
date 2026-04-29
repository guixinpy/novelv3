"""add subject knowledge fields

Revision ID: 20260429_add_subject_knowledge_fields
Revises: 20260429_add_writing_states
Create Date: 2026-04-29 18:30:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260429_add_subject_knowledge_fields"
down_revision: str | None = "20260429_add_writing_states"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("world_fact_claims", sa.Column("perspective_ref", sa.String(), nullable=True))
    op.add_column(
        "world_fact_claims",
        sa.Column("disclosed_to_refs", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column("world_proposal_items", sa.Column("perspective_ref", sa.String(), nullable=True))
    op.add_column(
        "world_proposal_items",
        sa.Column("disclosed_to_refs", sa.JSON(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("world_proposal_items", "disclosed_to_refs")
    op.drop_column("world_proposal_items", "perspective_ref")
    op.drop_column("world_fact_claims", "disclosed_to_refs")
    op.drop_column("world_fact_claims", "perspective_ref")
