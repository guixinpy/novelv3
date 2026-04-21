"""add world proposal tables

Revision ID: f7c1e2d3a4b5
Revises: e3b4d4b5c6a7
Create Date: 2026-04-20 23:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f7c1e2d3a4b5"
down_revision: Union[str, None] = "e3b4d4b5c6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_profile_binding_triggers(table_name: str) -> None:
    op.execute(
        f"""
        CREATE TRIGGER IF NOT EXISTS trg_{table_name}_profile_binding_insert
        BEFORE INSERT ON {table_name}
        WHEN NEW.project_profile_version_id IS NOT NULL
         AND NEW.profile_version IS NOT NULL
         AND NOT EXISTS (
            SELECT 1
            FROM project_profile_versions
            WHERE id = NEW.project_profile_version_id
              AND project_id = NEW.project_id
              AND version = NEW.profile_version
         )
        BEGIN
            SELECT RAISE(ABORT, '{table_name} profile binding mismatch');
        END;
        """
    )
    op.execute(
        f"""
        CREATE TRIGGER IF NOT EXISTS trg_{table_name}_profile_binding_update
        BEFORE UPDATE ON {table_name}
        WHEN NEW.project_profile_version_id IS NOT NULL
         AND NEW.profile_version IS NOT NULL
         AND NOT EXISTS (
            SELECT 1
            FROM project_profile_versions
            WHERE id = NEW.project_profile_version_id
              AND project_id = NEW.project_id
              AND version = NEW.profile_version
         )
        BEGIN
            SELECT RAISE(ABORT, '{table_name} profile binding mismatch');
        END;
        """
    )


def _drop_profile_binding_triggers(table_name: str) -> None:
    op.execute(f"DROP TRIGGER IF EXISTS trg_{table_name}_profile_binding_insert")
    op.execute(f"DROP TRIGGER IF EXISTS trg_{table_name}_profile_binding_update")


def _create_parent_item_lineage_triggers(table_name: str, *, bundle_table_name: str) -> None:
    op.execute(
        f"""
        CREATE TRIGGER IF NOT EXISTS trg_{table_name}_parent_item_lineage_insert
        BEFORE INSERT ON {table_name}
        WHEN NEW.parent_item_id IS NOT NULL
         AND NOT EXISTS (
            SELECT 1
            FROM {table_name} AS parent_item
            JOIN {bundle_table_name} AS child_bundle
              ON child_bundle.id = NEW.bundle_id
            WHERE parent_item.id = NEW.parent_item_id
              AND parent_item.project_id = NEW.project_id
              AND parent_item.project_profile_version_id = NEW.project_profile_version_id
              AND parent_item.profile_version = NEW.profile_version
              AND child_bundle.project_id = NEW.project_id
              AND child_bundle.project_profile_version_id = NEW.project_profile_version_id
              AND child_bundle.profile_version = NEW.profile_version
              AND child_bundle.parent_bundle_id = parent_item.bundle_id
         )
        BEGIN
            SELECT RAISE(ABORT, '{table_name} parent item lineage mismatch');
        END;
        """
    )
    op.execute(
        f"""
        CREATE TRIGGER IF NOT EXISTS trg_{table_name}_parent_item_lineage_update
        BEFORE UPDATE ON {table_name}
        WHEN NEW.parent_item_id IS NOT NULL
         AND NOT EXISTS (
            SELECT 1
            FROM {table_name} AS parent_item
            JOIN {bundle_table_name} AS child_bundle
              ON child_bundle.id = NEW.bundle_id
            WHERE parent_item.id = NEW.parent_item_id
              AND parent_item.project_id = NEW.project_id
              AND parent_item.project_profile_version_id = NEW.project_profile_version_id
              AND parent_item.profile_version = NEW.profile_version
              AND child_bundle.project_id = NEW.project_id
              AND child_bundle.project_profile_version_id = NEW.project_profile_version_id
              AND child_bundle.profile_version = NEW.profile_version
              AND child_bundle.parent_bundle_id = parent_item.bundle_id
         )
        BEGIN
            SELECT RAISE(ABORT, '{table_name} parent item lineage mismatch');
        END;
        """
    )


def _drop_parent_item_lineage_triggers(table_name: str) -> None:
    op.execute(f"DROP TRIGGER IF EXISTS trg_{table_name}_parent_item_lineage_insert")
    op.execute(f"DROP TRIGGER IF EXISTS trg_{table_name}_parent_item_lineage_update")


def upgrade() -> None:
    op.create_table(
        "world_proposal_bundles",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("project_profile_version_id", sa.String(), nullable=False),
        sa.Column("profile_version", sa.Integer(), nullable=False),
        sa.Column("parent_bundle_id", sa.String(), nullable=True),
        sa.Column("bundle_status", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["parent_bundle_id"], ["world_proposal_bundles.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["project_profile_version_id"], ["project_profile_versions.id"]),
        sa.ForeignKeyConstraint(
            ["parent_bundle_id", "project_id", "project_profile_version_id", "profile_version"],
            [
                "world_proposal_bundles.id",
                "world_proposal_bundles.project_id",
                "world_proposal_bundles.project_profile_version_id",
                "world_proposal_bundles.profile_version",
            ],
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "project_profile_version_id"],
            ["project_profile_versions.project_id", "project_profile_versions.id"],
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "profile_version"],
            ["project_profile_versions.project_id", "project_profile_versions.version"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "id",
            "project_id",
            "project_profile_version_id",
            "profile_version",
            name="uq_world_proposal_bundles_binding",
        ),
    )
    op.create_index(
        "ix_world_proposal_bundles_project_profile_version",
        "world_proposal_bundles",
        ["project_id", "profile_version"],
    )
    op.create_index(
        "ix_world_proposal_bundles_parent_bundle_id",
        "world_proposal_bundles",
        ["parent_bundle_id"],
    )

    op.create_table(
        "world_proposal_items",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("project_profile_version_id", sa.String(), nullable=False),
        sa.Column("profile_version", sa.Integer(), nullable=False),
        sa.Column("bundle_id", sa.String(), nullable=False),
        sa.Column("parent_item_id", sa.String(), nullable=True),
        sa.Column("item_status", sa.String(), nullable=False),
        sa.Column("claim_id", sa.String(), nullable=False),
        sa.Column("chapter_index", sa.Integer(), nullable=True),
        sa.Column("intra_chapter_seq", sa.Integer(), nullable=False),
        sa.Column("subject_ref", sa.String(), nullable=False),
        sa.Column("predicate", sa.String(), nullable=False),
        sa.Column("object_ref_or_value", sa.JSON(), nullable=False),
        sa.Column("claim_layer", sa.String(), nullable=False),
        sa.Column("valid_from_anchor_id", sa.String(), nullable=True),
        sa.Column("valid_to_anchor_id", sa.String(), nullable=True),
        sa.Column("source_event_ref", sa.String(), nullable=True),
        sa.Column("evidence_refs", sa.JSON(), nullable=True),
        sa.Column("authority_type", sa.String(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("contract_version", sa.String(), nullable=False),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("approved_claim_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["bundle_id"], ["world_proposal_bundles.id"]),
        sa.ForeignKeyConstraint(["parent_item_id"], ["world_proposal_items.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["project_profile_version_id"], ["project_profile_versions.id"]),
        sa.ForeignKeyConstraint(
            ["bundle_id", "project_id", "project_profile_version_id", "profile_version"],
            [
                "world_proposal_bundles.id",
                "world_proposal_bundles.project_id",
                "world_proposal_bundles.project_profile_version_id",
                "world_proposal_bundles.profile_version",
            ],
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "project_profile_version_id"],
            ["project_profile_versions.project_id", "project_profile_versions.id"],
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "profile_version"],
            ["project_profile_versions.project_id", "project_profile_versions.version"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "id",
            "bundle_id",
            "project_id",
            "project_profile_version_id",
            "profile_version",
            name="uq_world_proposal_items_binding",
        ),
    )
    op.create_index("ix_world_proposal_items_bundle_id", "world_proposal_items", ["bundle_id"])
    op.create_index("ix_world_proposal_items_parent_item_id", "world_proposal_items", ["parent_item_id"])
    op.create_index(
        "ix_world_proposal_items_project_profile_version",
        "world_proposal_items",
        ["project_id", "profile_version"],
    )
    _create_parent_item_lineage_triggers("world_proposal_items", bundle_table_name="world_proposal_bundles")

    op.create_table(
        "world_proposal_reviews",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("project_profile_version_id", sa.String(), nullable=False),
        sa.Column("profile_version", sa.Integer(), nullable=False),
        sa.Column("bundle_id", sa.String(), nullable=False),
        sa.Column("proposal_item_id", sa.String(), nullable=True),
        sa.Column("review_action", sa.String(), nullable=False),
        sa.Column("reviewer_ref", sa.String(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("evidence_refs", sa.JSON(), nullable=True),
        sa.Column("edited_fields", sa.JSON(), nullable=True),
        sa.Column("created_truth_claim_id", sa.String(), nullable=True),
        sa.Column("rollback_to_review_id", sa.String(), nullable=True),
        sa.Column("metadata_snapshot", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["bundle_id"], ["world_proposal_bundles.id"]),
        sa.ForeignKeyConstraint(["proposal_item_id"], ["world_proposal_items.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["project_profile_version_id"], ["project_profile_versions.id"]),
        sa.ForeignKeyConstraint(["rollback_to_review_id"], ["world_proposal_reviews.id"]),
        sa.ForeignKeyConstraint(
            ["bundle_id", "project_id", "project_profile_version_id", "profile_version"],
            [
                "world_proposal_bundles.id",
                "world_proposal_bundles.project_id",
                "world_proposal_bundles.project_profile_version_id",
                "world_proposal_bundles.profile_version",
            ],
        ),
        sa.ForeignKeyConstraint(
            ["proposal_item_id", "bundle_id", "project_id", "project_profile_version_id", "profile_version"],
            [
                "world_proposal_items.id",
                "world_proposal_items.bundle_id",
                "world_proposal_items.project_id",
                "world_proposal_items.project_profile_version_id",
                "world_proposal_items.profile_version",
            ],
        ),
        sa.ForeignKeyConstraint(
            ["rollback_to_review_id", "bundle_id", "project_id", "project_profile_version_id", "profile_version"],
            [
                "world_proposal_reviews.id",
                "world_proposal_reviews.bundle_id",
                "world_proposal_reviews.project_id",
                "world_proposal_reviews.project_profile_version_id",
                "world_proposal_reviews.profile_version",
            ],
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "project_profile_version_id"],
            ["project_profile_versions.project_id", "project_profile_versions.id"],
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "profile_version"],
            ["project_profile_versions.project_id", "project_profile_versions.version"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "id",
            "bundle_id",
            "project_id",
            "project_profile_version_id",
            "profile_version",
            name="uq_world_proposal_reviews_binding",
        ),
        sa.UniqueConstraint("rollback_to_review_id", name="uq_world_proposal_reviews_rollback_to_review_id"),
    )
    op.create_index("ix_world_proposal_reviews_bundle_id", "world_proposal_reviews", ["bundle_id"])
    op.create_index("ix_world_proposal_reviews_item_id", "world_proposal_reviews", ["proposal_item_id"])

    op.create_table(
        "world_proposal_impact_scope_snapshots",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("project_profile_version_id", sa.String(), nullable=False),
        sa.Column("profile_version", sa.Integer(), nullable=False),
        sa.Column("bundle_id", sa.String(), nullable=False),
        sa.Column("affected_subject_refs", sa.JSON(), nullable=True),
        sa.Column("affected_predicates", sa.JSON(), nullable=True),
        sa.Column("affected_truth_claim_ids", sa.JSON(), nullable=True),
        sa.Column("candidate_item_ids", sa.JSON(), nullable=True),
        sa.Column("summary", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["bundle_id"], ["world_proposal_bundles.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["project_profile_version_id"], ["project_profile_versions.id"]),
        sa.ForeignKeyConstraint(
            ["project_id", "project_profile_version_id"],
            ["project_profile_versions.project_id", "project_profile_versions.id"],
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "profile_version"],
            ["project_profile_versions.project_id", "project_profile_versions.version"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_world_proposal_impact_scope_bundle_id",
        "world_proposal_impact_scope_snapshots",
        ["bundle_id"],
    )

    _create_profile_binding_triggers("world_proposal_bundles")
    _create_profile_binding_triggers("world_proposal_items")
    _create_profile_binding_triggers("world_proposal_reviews")
    _create_profile_binding_triggers("world_proposal_impact_scope_snapshots")


def downgrade() -> None:
    _drop_parent_item_lineage_triggers("world_proposal_items")
    _drop_profile_binding_triggers("world_proposal_impact_scope_snapshots")
    _drop_profile_binding_triggers("world_proposal_reviews")
    _drop_profile_binding_triggers("world_proposal_items")
    _drop_profile_binding_triggers("world_proposal_bundles")

    op.drop_index("ix_world_proposal_impact_scope_bundle_id", table_name="world_proposal_impact_scope_snapshots")
    op.drop_table("world_proposal_impact_scope_snapshots")

    op.drop_index("ix_world_proposal_reviews_item_id", table_name="world_proposal_reviews")
    op.drop_index("ix_world_proposal_reviews_bundle_id", table_name="world_proposal_reviews")
    op.drop_table("world_proposal_reviews")

    op.drop_index("ix_world_proposal_items_project_profile_version", table_name="world_proposal_items")
    op.drop_index("ix_world_proposal_items_parent_item_id", table_name="world_proposal_items")
    op.drop_index("ix_world_proposal_items_bundle_id", table_name="world_proposal_items")
    op.drop_table("world_proposal_items")

    op.drop_index("ix_world_proposal_bundles_parent_bundle_id", table_name="world_proposal_bundles")
    op.drop_index("ix_world_proposal_bundles_project_profile_version", table_name="world_proposal_bundles")
    op.drop_table("world_proposal_bundles")
