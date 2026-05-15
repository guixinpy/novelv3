"""add proposal item status index

Revision ID: 20260515_add_proposal_item_status_index
Revises: 20260515_add_world_projection_hot_indexes
Create Date: 2026-05-15 11:52:00.000000

"""
from collections.abc import Sequence

from alembic import op


revision: str = "20260515_add_proposal_item_status_index"
down_revision: str | None = "20260515_add_world_projection_hot_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_world_proposal_items_project_profile_status_order",
        "world_proposal_items",
        [
            "project_id",
            "project_profile_version_id",
            "profile_version",
            "item_status",
            "chapter_index",
            "predicate",
            "subject_ref",
            "id",
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_world_proposal_items_project_profile_status_order", table_name="world_proposal_items")
