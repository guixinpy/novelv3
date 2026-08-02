"""add longform memories

Revision ID: 20260513_add_longform_memories
Revises: 20260429_add_retrieval_terms
Create Date: 2026-05-13 13:20:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op


revision: str = "20260513_add_longform_memories"
down_revision: str | None = "20260429_add_retrieval_terms"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "longform_memories",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("memory_type", sa.String(), nullable=False),
        sa.Column("scope_key", sa.String(), nullable=False),
        sa.Column("start_chapter_index", sa.Integer(), nullable=True),
        sa.Column("end_chapter_index", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("memory_metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "memory_type", "scope_key", name="uq_longform_memories_scope"),
    )
    op.create_index("ix_longform_memories_project_type", "longform_memories", ["project_id", "memory_type"])
    op.create_index(
        "ix_longform_memories_project_range",
        "longform_memories",
        ["project_id", "start_chapter_index", "end_chapter_index"],
    )


def downgrade() -> None:
    op.drop_index("ix_longform_memories_project_range", table_name="longform_memories")
    op.drop_index("ix_longform_memories_project_type", table_name="longform_memories")
    op.drop_table("longform_memories")
