"""add background task active lookup index

Revision ID: 20260517_add_background_task_active_lookup_index
Revises: 20260515_add_proposal_item_status_index
Create Date: 2026-05-17 13:36:00.000000

"""
from collections.abc import Sequence

from alembic import op


revision: str = "20260517_add_background_task_active_lookup_index"
down_revision: str | None = "20260515_add_proposal_item_status_index"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_background_tasks_project_type_status_created",
        "background_tasks",
        ["project_id", "task_type", "status", "created_at", "id"],
    )


def downgrade() -> None:
    op.drop_index("ix_background_tasks_project_type_status_created", table_name="background_tasks")
