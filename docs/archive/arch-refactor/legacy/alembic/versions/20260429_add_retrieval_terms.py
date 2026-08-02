"""add retrieval lexical term index

Revision ID: 20260429_add_retrieval_terms
Revises: 20260429_add_subject_knowledge_fields
Create Date: 2026-04-29 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260429_add_retrieval_terms"
down_revision: str | None = "20260429_add_subject_knowledge_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "retrieval_terms",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("chunk_id", sa.String(), nullable=False),
        sa.Column("token", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["chunk_id"], ["retrieval_chunks.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "chunk_id", "token", name="uq_retrieval_terms_project_chunk_token"),
    )
    op.create_index("ix_retrieval_terms_project_token", "retrieval_terms", ["project_id", "token"])
    op.create_index("ix_retrieval_terms_chunk", "retrieval_terms", ["chunk_id"])


def downgrade() -> None:
    op.drop_index("ix_retrieval_terms_chunk", table_name="retrieval_terms")
    op.drop_index("ix_retrieval_terms_project_token", table_name="retrieval_terms")
    op.drop_table("retrieval_terms")
