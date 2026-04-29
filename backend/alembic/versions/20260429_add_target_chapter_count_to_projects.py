"""add target chapter count to projects

Revision ID: 20260429_add_target_chapter_count_to_projects
Revises: 20260428_add_ai_model_call_traces
Create Date: 2026-04-29 10:20:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260429_add_target_chapter_count_to_projects"
down_revision: str | None = "20260428_add_ai_model_call_traces"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("target_chapter_count", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("projects", "target_chapter_count")
