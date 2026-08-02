"""add writing agent step bindings

Revision ID: 20260523_add_writing_agent_step_bindings
Revises: 20260518_add_writing_agent_runs
Create Date: 2026-05-23 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op


revision: str = "20260523_add_writing_agent_step_bindings"
down_revision: str | None = "20260518_add_writing_agent_runs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("writing_agent_steps", sa.Column("tool_call_id", sa.String(), nullable=True))
    op.add_column("writing_agent_steps", sa.Column("resource_binding", sa.JSON(), nullable=True))
    op.create_index(
        "ix_writing_agent_steps_project_tool_call",
        "writing_agent_steps",
        ["project_id", "tool_call_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_writing_agent_steps_project_tool_call", table_name="writing_agent_steps")
    op.drop_column("writing_agent_steps", "resource_binding")
    op.drop_column("writing_agent_steps", "tool_call_id")
