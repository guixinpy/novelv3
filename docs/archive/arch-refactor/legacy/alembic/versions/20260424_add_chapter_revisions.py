"""add chapter revisions

Revision ID: 20260424_add_chapter_revisions
Revises: bfe0f1ff2e2d
Create Date: 2026-04-24 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260424_add_chapter_revisions"
down_revision: str | None = "bfe0f1ff2e2d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "chapter_revisions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("chapter_id", sa.String(), nullable=False),
        sa.Column("chapter_index", sa.Integer(), nullable=False),
        sa.Column("revision_index", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapter_contents.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_chapter_revisions_project_chapter",
        "chapter_revisions",
        ["project_id", "chapter_index"],
    )
    op.create_index(
        "ix_chapter_revisions_project_chapter_revision",
        "chapter_revisions",
        ["project_id", "chapter_index", "revision_index"],
        unique=True,
    )
    op.create_table(
        "revision_annotations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("revision_id", sa.String(), nullable=False),
        sa.Column("paragraph_index", sa.Integer(), nullable=False),
        sa.Column("start_offset", sa.Integer(), nullable=False),
        sa.Column("end_offset", sa.Integer(), nullable=False),
        sa.Column("selected_text", sa.Text(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["revision_id"], ["chapter_revisions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_revision_annotations_revision_id", "revision_annotations", ["revision_id"])
    op.create_table(
        "revision_corrections",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("revision_id", sa.String(), nullable=False),
        sa.Column("paragraph_index", sa.Integer(), nullable=False),
        sa.Column("original_text", sa.Text(), nullable=False),
        sa.Column("corrected_text", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["revision_id"], ["chapter_revisions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_revision_corrections_revision_id", "revision_corrections", ["revision_id"])


def downgrade() -> None:
    op.drop_index("ix_revision_corrections_revision_id", table_name="revision_corrections")
    op.drop_table("revision_corrections")
    op.drop_index("ix_revision_annotations_revision_id", table_name="revision_annotations")
    op.drop_table("revision_annotations")
    op.drop_index("ix_chapter_revisions_project_chapter_revision", table_name="chapter_revisions")
    op.drop_index("ix_chapter_revisions_project_chapter", table_name="chapter_revisions")
    op.drop_table("chapter_revisions")
