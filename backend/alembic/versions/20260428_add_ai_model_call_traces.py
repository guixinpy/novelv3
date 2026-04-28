"""add ai model call traces

Revision ID: 20260428_add_ai_model_call_traces
Revises: 20260428_add_athena_retrieval_tables
Create Date: 2026-04-28 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260428_add_ai_model_call_traces"
down_revision: str | None = "20260428_add_athena_retrieval_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_model_call_traces",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("trace_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("temperature", sa.Float(), nullable=True),
        sa.Column("max_tokens", sa.Integer(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("dialog_id", sa.String(), nullable=True),
        sa.Column("request_message_id", sa.String(), nullable=True),
        sa.Column("response_message_id", sa.String(), nullable=True),
        sa.Column("chapter_id", sa.String(), nullable=True),
        sa.Column("chapter_index", sa.Integer(), nullable=True),
        sa.Column("messages", sa.JSON(), nullable=True),
        sa.Column("context_blocks", sa.JSON(), nullable=True),
        sa.Column("trace_metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapter_contents.id"]),
        sa.ForeignKeyConstraint(["dialog_id"], ["dialogs.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["request_message_id"], ["dialog_messages.id"]),
        sa.ForeignKeyConstraint(["response_message_id"], ["dialog_messages.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ai_model_call_traces_project_created",
        "ai_model_call_traces",
        ["project_id", "created_at"],
    )
    op.create_index(
        "ix_ai_model_call_traces_project_type",
        "ai_model_call_traces",
        ["project_id", "trace_type"],
    )
    op.create_index("ix_ai_model_call_traces_dialog", "ai_model_call_traces", ["dialog_id"])


def downgrade() -> None:
    op.drop_index("ix_ai_model_call_traces_dialog", table_name="ai_model_call_traces")
    op.drop_index("ix_ai_model_call_traces_project_type", table_name="ai_model_call_traces")
    op.drop_index("ix_ai_model_call_traces_project_created", table_name="ai_model_call_traces")
    op.drop_table("ai_model_call_traces")
