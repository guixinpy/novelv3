"""add writing states

Revision ID: 20260429_add_writing_states
Revises: 20260429_add_target_chapter_count_to_projects
Create Date: 2026-04-29 16:45:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260429_add_writing_states"
down_revision: str | None = "20260429_add_target_chapter_count_to_projects"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "writing_states",
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("current_chapter", sa.Integer(), server_default="1", nullable=False),
        sa.Column("status", sa.String(), server_default="idle", nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("project_id"),
    )


def downgrade() -> None:
    op.drop_table("writing_states")

