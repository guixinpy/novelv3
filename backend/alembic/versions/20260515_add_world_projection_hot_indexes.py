"""add world projection hot indexes

Revision ID: 20260515_add_world_projection_hot_indexes
Revises: 20260513_add_longform_hot_indexes
Create Date: 2026-05-15 11:45:00.000000

"""
from collections.abc import Sequence

from alembic import op


revision: str = "20260515_add_world_projection_hot_indexes"
down_revision: str | None = "20260513_add_longform_hot_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_world_timeline_anchors_project_profile_order",
        "world_timeline_anchors",
        ["project_id", "profile_version", "chapter_index", "intra_chapter_seq", "anchor_id"],
    )
    op.create_index(
        "ix_world_events_project_profile_order",
        "world_events",
        [
            "project_id",
            "project_profile_version_id",
            "profile_version",
            "chapter_index",
            "intra_chapter_seq",
            "event_id",
        ],
    )
    op.create_index(
        "ix_world_fact_claims_project_profile_status_order",
        "world_fact_claims",
        [
            "project_id",
            "project_profile_version_id",
            "profile_version",
            "claim_status",
            "claim_layer",
            "chapter_index",
            "intra_chapter_seq",
            "claim_id",
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_world_fact_claims_project_profile_status_order", table_name="world_fact_claims")
    op.drop_index("ix_world_events_project_profile_order", table_name="world_events")
    op.drop_index("ix_world_timeline_anchors_project_profile_order", table_name="world_timeline_anchors")
