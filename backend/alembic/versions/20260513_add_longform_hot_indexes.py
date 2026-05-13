"""add longform hot table indexes

Revision ID: 20260513_add_longform_hot_indexes
Revises: 20260513_add_longform_memories
Create Date: 2026-05-13 18:40:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op


revision: str = "20260513_add_longform_hot_indexes"
down_revision: str | None = "20260513_add_longform_memories"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_chapter_contents_project_chapter",
        "chapter_contents",
        ["project_id", "chapter_index"],
    )
    op.create_index(
        "ix_chapter_contents_project_status",
        "chapter_contents",
        ["project_id", "status"],
    )
    op.create_index(
        "ix_dialog_messages_dialog_type_created",
        "dialog_messages",
        ["dialog_id", "message_type", "created_at", "id"],
    )
    op.create_index(
        "ix_dialog_messages_dialog_action_created",
        "dialog_messages",
        ["dialog_id", "created_at", "id"],
        sqlite_where=sa.text("action_result IS NOT NULL"),
    )
    op.create_index(
        "ix_consistency_checks_project_chapter",
        "consistency_checks",
        ["project_id", "chapter_index"],
    )
    op.create_index(
        "ix_consistency_checks_project_status",
        "consistency_checks",
        ["project_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_consistency_checks_project_status", table_name="consistency_checks")
    op.drop_index("ix_consistency_checks_project_chapter", table_name="consistency_checks")
    op.drop_index("ix_dialog_messages_dialog_action_created", table_name="dialog_messages")
    op.drop_index("ix_dialog_messages_dialog_type_created", table_name="dialog_messages")
    op.drop_index("ix_chapter_contents_project_status", table_name="chapter_contents")
    op.drop_index("ix_chapter_contents_project_chapter", table_name="chapter_contents")
