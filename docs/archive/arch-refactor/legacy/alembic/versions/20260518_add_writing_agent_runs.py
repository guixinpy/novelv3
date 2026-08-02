"""add writing agent run tables

Revision ID: 20260518_add_writing_agent_runs
Revises: 20260517_add_background_task_active_lookup_index
Create Date: 2026-05-18 18:30:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op


revision: str = "20260518_add_writing_agent_runs"
down_revision: str | None = "20260517_add_background_task_active_lookup_index"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "writing_agent_runs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("entrypoint", sa.String(), nullable=False),
        sa.Column("input", sa.JSON(), nullable=True),
        sa.Column("output", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("background_task_id", sa.String(), nullable=True),
        sa.Column("dialog_id", sa.String(), nullable=True),
        sa.Column("request_message_id", sa.String(), nullable=True),
        sa.Column("response_message_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["background_task_id"], ["background_tasks.id"]),
        sa.ForeignKeyConstraint(["dialog_id"], ["dialogs.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["request_message_id"], ["dialog_messages.id"]),
        sa.ForeignKeyConstraint(["response_message_id"], ["dialog_messages.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_writing_agent_runs_project_created",
        "writing_agent_runs",
        ["project_id", "created_at", "id"],
    )
    op.create_index(
        "ix_writing_agent_runs_project_status_created",
        "writing_agent_runs",
        ["project_id", "status", "created_at", "id"],
    )

    op.create_table(
        "writing_agent_steps",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("step_index", sa.Integer(), nullable=False),
        sa.Column("tool_name", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("input", sa.JSON(), nullable=True),
        sa.Column("output", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("trace_id", sa.String(), nullable=True),
        sa.Column("background_task_id", sa.String(), nullable=True),
        sa.Column("target_type", sa.String(), nullable=True),
        sa.Column("target_id", sa.String(), nullable=True),
        sa.Column("chapter_index", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["background_task_id"], ["background_tasks.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["run_id"], ["writing_agent_runs.id"]),
        sa.ForeignKeyConstraint(["trace_id"], ["ai_model_call_traces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_writing_agent_steps_run_order",
        "writing_agent_steps",
        ["run_id", "step_index", "id"],
    )
    op.create_index(
        "ix_writing_agent_steps_project_tool_created",
        "writing_agent_steps",
        ["project_id", "tool_name", "created_at", "id"],
    )


def downgrade() -> None:
    op.drop_index("ix_writing_agent_steps_project_tool_created", table_name="writing_agent_steps")
    op.drop_index("ix_writing_agent_steps_run_order", table_name="writing_agent_steps")
    op.drop_table("writing_agent_steps")
    op.drop_index("ix_writing_agent_runs_project_status_created", table_name="writing_agent_runs")
    op.drop_index("ix_writing_agent_runs_project_created", table_name="writing_agent_runs")
    op.drop_table("writing_agent_runs")
