"""add world model stage1 tables

Revision ID: e3b4d4b5c6a7
Revises: d9f5e6a1c2b3
Create Date: 2026-04-20 17:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e3b4d4b5c6a7"
down_revision: Union[str, None] = "d9f5e6a1c2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "genre_profiles",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("canonical_id", sa.String(), nullable=False),
        sa.Column("primary_alias", sa.String(), nullable=True),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("contract_version", sa.String(), nullable=False),
        sa.Column("field_authority", sa.JSON(), nullable=True),
        sa.Column("schema_payload", sa.JSON(), nullable=True),
        sa.Column("module_payload", sa.JSON(), nullable=True),
        sa.Column("event_types", sa.JSON(), nullable=True),
        sa.Column("checker_config", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("canonical_id", name="uq_genre_profiles_canonical_id"),
    )
    op.create_index("ix_genre_profiles_canonical_id", "genre_profiles", ["canonical_id"])
    op.create_index("ix_genre_profiles_primary_alias", "genre_profiles", ["primary_alias"])

    op.create_table(
        "project_profile_versions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("genre_profile_id", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("contract_version", sa.String(), nullable=False),
        sa.Column("profile_payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint("version >= 1", name="ck_project_profile_versions_version_gte_1"),
        sa.ForeignKeyConstraint(["genre_profile_id"], ["genre_profiles.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "id", name="uq_project_profile_versions_project_id_id"),
        sa.UniqueConstraint("project_id", "version", name="uq_project_profile_versions_project_version"),
    )
    op.create_index(
        "ix_project_profile_versions_project_version",
        "project_profile_versions",
        ["project_id", "version"],
    )
    op.execute(
        """
        CREATE TRIGGER IF NOT EXISTS trg_project_profile_versions_contract_version_insert
        BEFORE INSERT ON project_profile_versions
        WHEN EXISTS (
            SELECT 1
            FROM genre_profiles
            WHERE id = NEW.genre_profile_id
              AND contract_version <> NEW.contract_version
        )
        BEGIN
            SELECT RAISE(ABORT, 'project_profile_versions contract_version mismatch');
        END;
        """
    )
    op.execute(
        """
        CREATE TRIGGER IF NOT EXISTS trg_project_profile_versions_append_only
        BEFORE UPDATE ON project_profile_versions
        BEGIN
            SELECT RAISE(ABORT, 'project_profile_versions is append-only');
        END;
        """
    )
    op.execute(
        """
        CREATE TRIGGER IF NOT EXISTS trg_project_profile_versions_append_only_delete
        BEFORE DELETE ON project_profile_versions
        BEGIN
            SELECT RAISE(ABORT, 'project_profile_versions is append-only');
        END;
        """
    )

    op.create_table(
        "world_characters",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("profile_version", sa.Integer(), nullable=False),
        sa.Column("character_id", sa.String(), nullable=False),
        sa.Column("canonical_id", sa.String(), nullable=False),
        sa.Column("primary_alias", sa.String(), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("aliases", sa.JSON(), nullable=True),
        sa.Column("role_type", sa.String(), nullable=False),
        sa.Column("identity_anchor", sa.String(), nullable=False),
        sa.Column("origin_background", sa.Text(), nullable=True),
        sa.Column("core_traits", sa.JSON(), nullable=True),
        sa.Column("core_drives", sa.JSON(), nullable=True),
        sa.Column("core_fears", sa.JSON(), nullable=True),
        sa.Column("taboos_or_bottom_lines", sa.JSON(), nullable=True),
        sa.Column("base_capabilities", sa.JSON(), nullable=True),
        sa.Column("capability_ceiling_or_constraints", sa.JSON(), nullable=True),
        sa.Column("default_affiliations", sa.JSON(), nullable=True),
        sa.Column("public_persona", sa.Text(), nullable=True),
        sa.Column("hidden_truths", sa.JSON(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("contract_version", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["project_id", "profile_version"], ["project_profile_versions.project_id", "project_profile_versions.version"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "profile_version", "canonical_id", name="uq_world_characters_project_profile_canonical"),
        sa.UniqueConstraint("project_id", "profile_version", "character_id", name="uq_world_characters_project_profile_character_id"),
    )
    op.create_index("ix_world_characters_project_profile_version", "world_characters", ["project_id", "profile_version"])
    op.create_index("ix_world_characters_canonical_id", "world_characters", ["canonical_id"])
    op.create_index("ix_world_characters_primary_alias", "world_characters", ["primary_alias"])

    op.create_table(
        "world_locations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("profile_version", sa.Integer(), nullable=False),
        sa.Column("location_id", sa.String(), nullable=False),
        sa.Column("canonical_id", sa.String(), nullable=False),
        sa.Column("primary_alias", sa.String(), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("aliases", sa.JSON(), nullable=True),
        sa.Column("location_type", sa.String(), nullable=False),
        sa.Column("parent_location_id", sa.String(), nullable=True),
        sa.Column("spatial_scope", sa.Text(), nullable=True),
        sa.Column("access_constraints", sa.JSON(), nullable=True),
        sa.Column("functional_tags", sa.JSON(), nullable=True),
        sa.Column("hazards", sa.JSON(), nullable=True),
        sa.Column("resource_tags", sa.JSON(), nullable=True),
        sa.Column("surveillance_or_visibility_level", sa.String(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("contract_version", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["project_id", "profile_version"], ["project_profile_versions.project_id", "project_profile_versions.version"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "profile_version", "canonical_id", name="uq_world_locations_project_profile_canonical"),
        sa.UniqueConstraint("project_id", "profile_version", "location_id", name="uq_world_locations_project_profile_location_id"),
    )
    op.create_index("ix_world_locations_project_profile_version", "world_locations", ["project_id", "profile_version"])
    op.create_index("ix_world_locations_canonical_id", "world_locations", ["canonical_id"])
    op.create_index("ix_world_locations_primary_alias", "world_locations", ["primary_alias"])

    op.create_table(
        "world_factions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("profile_version", sa.Integer(), nullable=False),
        sa.Column("faction_id", sa.String(), nullable=False),
        sa.Column("canonical_id", sa.String(), nullable=False),
        sa.Column("primary_alias", sa.String(), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("aliases", sa.JSON(), nullable=True),
        sa.Column("faction_type", sa.String(), nullable=False),
        sa.Column("mission_or_doctrine", sa.Text(), nullable=True),
        sa.Column("structure_model", sa.String(), nullable=True),
        sa.Column("authority_rules", sa.JSON(), nullable=True),
        sa.Column("membership_rules", sa.JSON(), nullable=True),
        sa.Column("taboos", sa.JSON(), nullable=True),
        sa.Column("resource_domains", sa.JSON(), nullable=True),
        sa.Column("territorial_scope", sa.Text(), nullable=True),
        sa.Column("public_image", sa.Text(), nullable=True),
        sa.Column("hidden_agenda", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("contract_version", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["project_id", "profile_version"], ["project_profile_versions.project_id", "project_profile_versions.version"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "profile_version", "canonical_id", name="uq_world_factions_project_profile_canonical"),
        sa.UniqueConstraint("project_id", "profile_version", "faction_id", name="uq_world_factions_project_profile_faction_id"),
    )
    op.create_index("ix_world_factions_project_profile_version", "world_factions", ["project_id", "profile_version"])
    op.create_index("ix_world_factions_canonical_id", "world_factions", ["canonical_id"])
    op.create_index("ix_world_factions_primary_alias", "world_factions", ["primary_alias"])

    op.create_table(
        "world_artifacts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("profile_version", sa.Integer(), nullable=False),
        sa.Column("artifact_id", sa.String(), nullable=False),
        sa.Column("canonical_id", sa.String(), nullable=False),
        sa.Column("primary_alias", sa.String(), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("aliases", sa.JSON(), nullable=True),
        sa.Column("artifact_type", sa.String(), nullable=False),
        sa.Column("origin", sa.Text(), nullable=True),
        sa.Column("function_summary", sa.Text(), nullable=True),
        sa.Column("activation_conditions", sa.JSON(), nullable=True),
        sa.Column("usage_constraints", sa.JSON(), nullable=True),
        sa.Column("risk_or_side_effects", sa.JSON(), nullable=True),
        sa.Column("identity_or_auth_requirements", sa.JSON(), nullable=True),
        sa.Column("uniqueness", sa.String(), nullable=True),
        sa.Column("traceability", sa.String(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("contract_version", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["project_id", "profile_version"], ["project_profile_versions.project_id", "project_profile_versions.version"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "profile_version", "artifact_id", name="uq_world_artifacts_project_profile_artifact_id"),
        sa.UniqueConstraint("project_id", "profile_version", "canonical_id", name="uq_world_artifacts_project_profile_canonical"),
    )
    op.create_index("ix_world_artifacts_project_profile_version", "world_artifacts", ["project_id", "profile_version"])
    op.create_index("ix_world_artifacts_canonical_id", "world_artifacts", ["canonical_id"])
    op.create_index("ix_world_artifacts_primary_alias", "world_artifacts", ["primary_alias"])

    op.create_table(
        "world_rules",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("profile_version", sa.Integer(), nullable=False),
        sa.Column("rule_id", sa.String(), nullable=False),
        sa.Column("canonical_id", sa.String(), nullable=False),
        sa.Column("primary_alias", sa.String(), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("rule_type", sa.String(), nullable=False),
        sa.Column("scope", sa.Text(), nullable=True),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("preconditions", sa.JSON(), nullable=True),
        sa.Column("effects", sa.JSON(), nullable=True),
        sa.Column("constraints", sa.JSON(), nullable=True),
        sa.Column("exceptions", sa.JSON(), nullable=True),
        sa.Column("violation_cost", sa.Text(), nullable=True),
        sa.Column("enforcement_agent", sa.String(), nullable=True),
        sa.Column("repair_or_override_path", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("contract_version", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["project_id", "profile_version"], ["project_profile_versions.project_id", "project_profile_versions.version"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "profile_version", "canonical_id", name="uq_world_rules_project_profile_canonical"),
        sa.UniqueConstraint("project_id", "profile_version", "rule_id", name="uq_world_rules_project_profile_rule_id"),
    )
    op.create_index("ix_world_rules_project_profile_version", "world_rules", ["project_id", "profile_version"])
    op.create_index("ix_world_rules_canonical_id", "world_rules", ["canonical_id"])
    op.create_index("ix_world_rules_primary_alias", "world_rules", ["primary_alias"])

    op.create_table(
        "world_resources",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("profile_version", sa.Integer(), nullable=False),
        sa.Column("resource_id", sa.String(), nullable=False),
        sa.Column("canonical_id", sa.String(), nullable=False),
        sa.Column("primary_alias", sa.String(), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("resource_type", sa.String(), nullable=False),
        sa.Column("unit_or_scale", sa.String(), nullable=True),
        sa.Column("holder_type", sa.String(), nullable=True),
        sa.Column("acquisition_paths", sa.JSON(), nullable=True),
        sa.Column("consumption_paths", sa.JSON(), nullable=True),
        sa.Column("scarcity_level", sa.String(), nullable=True),
        sa.Column("renewal_model", sa.String(), nullable=True),
        sa.Column("transferability", sa.String(), nullable=True),
        sa.Column("visibility", sa.String(), nullable=True),
        sa.Column("critical_threshold_effect", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("contract_version", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["project_id", "profile_version"], ["project_profile_versions.project_id", "project_profile_versions.version"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "profile_version", "canonical_id", name="uq_world_resources_project_profile_canonical"),
        sa.UniqueConstraint("project_id", "profile_version", "resource_id", name="uq_world_resources_project_profile_resource_id"),
    )
    op.create_index("ix_world_resources_project_profile_version", "world_resources", ["project_id", "profile_version"])
    op.create_index("ix_world_resources_canonical_id", "world_resources", ["canonical_id"])
    op.create_index("ix_world_resources_primary_alias", "world_resources", ["primary_alias"])

    op.create_table(
        "world_relations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("profile_version", sa.Integer(), nullable=False),
        sa.Column("relation_id", sa.String(), nullable=False),
        sa.Column("source_entity_ref", sa.String(), nullable=False),
        sa.Column("target_entity_ref", sa.String(), nullable=False),
        sa.Column("relation_type", sa.String(), nullable=False),
        sa.Column("directionality", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("visibility_layer", sa.String(), nullable=False),
        sa.Column("strength_or_weight", sa.String(), nullable=True),
        sa.Column("start_anchor_id", sa.String(), nullable=True),
        sa.Column("end_anchor_id", sa.String(), nullable=True),
        sa.Column("evidence_refs", sa.JSON(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("contract_version", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["project_id", "profile_version"], ["project_profile_versions.project_id", "project_profile_versions.version"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "profile_version", "relation_id", name="uq_world_relations_project_profile_relation_id"),
    )
    op.create_index("ix_world_relations_project_profile_version", "world_relations", ["project_id", "profile_version"])
    op.create_index("ix_world_relations_relation_id", "world_relations", ["relation_id"])

    op.create_table(
        "world_timeline_anchors",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("profile_version", sa.Integer(), nullable=False),
        sa.Column("anchor_id", sa.String(), nullable=False),
        sa.Column("chapter_index", sa.Integer(), nullable=True),
        sa.Column("intra_chapter_seq", sa.Integer(), nullable=False),
        sa.Column("world_time_label", sa.String(), nullable=True),
        sa.Column("normalized_tick_or_range", sa.String(), nullable=True),
        sa.Column("precision", sa.String(), nullable=True),
        sa.Column("relative_to_anchor_ref", sa.String(), nullable=True),
        sa.Column("ordering_key", sa.String(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("contract_version", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["project_id", "profile_version"], ["project_profile_versions.project_id", "project_profile_versions.version"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "profile_version", "anchor_id", name="uq_world_timeline_anchors_project_profile_anchor_id"),
    )
    op.create_index("ix_world_timeline_anchors_project_profile_version", "world_timeline_anchors", ["project_id", "profile_version"])
    op.create_index("ix_world_timeline_anchors_anchor_id", "world_timeline_anchors", ["anchor_id"])
    op.create_index("ix_world_timeline_anchors_chapter_seq", "world_timeline_anchors", ["chapter_index", "intra_chapter_seq"])

    op.create_table(
        "world_events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("project_profile_version_id", sa.String(), nullable=True),
        sa.Column("profile_version", sa.Integer(), nullable=True),
        sa.Column("event_id", sa.String(), nullable=False),
        sa.Column("idempotency_key", sa.String(), nullable=True),
        sa.Column("timeline_anchor_id", sa.String(), nullable=False),
        sa.Column("chapter_index", sa.Integer(), nullable=False),
        sa.Column("intra_chapter_seq", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("participant_refs", sa.JSON(), nullable=True),
        sa.Column("location_refs", sa.JSON(), nullable=True),
        sa.Column("precondition_event_refs", sa.JSON(), nullable=True),
        sa.Column("caused_event_refs", sa.JSON(), nullable=True),
        sa.Column("primitive_payload", sa.JSON(), nullable=True),
        sa.Column("state_diffs", sa.JSON(), nullable=True),
        sa.Column("truth_layer", sa.String(), nullable=False),
        sa.Column("disclosure_layer", sa.String(), nullable=False),
        sa.Column("evidence_refs", sa.JSON(), nullable=True),
        sa.Column("contract_version_refs", sa.JSON(), nullable=True),
        sa.Column("supersedes_event_ref", sa.String(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("contract_version", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint("profile_version IS NOT NULL OR project_profile_version_id IS NOT NULL", name="ck_world_events_has_profile_version_binding"),
        sa.ForeignKeyConstraint(["project_id", "profile_version"], ["project_profile_versions.project_id", "project_profile_versions.version"]),
        sa.ForeignKeyConstraint(["project_id", "project_profile_version_id"], ["project_profile_versions.project_id", "project_profile_versions.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["project_id", "supersedes_event_ref"], ["world_events.project_id", "world_events.event_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "idempotency_key", name="uq_world_events_project_idempotency_key"),
        sa.UniqueConstraint("project_id", "event_id", name="uq_world_events_project_event_id"),
    )
    op.create_index("ix_world_events_project_profile_version", "world_events", ["project_id", "profile_version"])
    op.create_index("ix_world_events_chapter_seq", "world_events", ["chapter_index", "intra_chapter_seq"])
    op.execute(
        """
        CREATE TRIGGER IF NOT EXISTS trg_world_events_profile_binding_insert
        BEFORE INSERT ON world_events
        WHEN NEW.project_profile_version_id IS NOT NULL
         AND NEW.profile_version IS NOT NULL
         AND NOT EXISTS (
            SELECT 1 FROM project_profile_versions
            WHERE id = NEW.project_profile_version_id
              AND project_id = NEW.project_id
              AND version = NEW.profile_version
         )
        BEGIN
            SELECT RAISE(ABORT, 'world_events profile binding mismatch');
        END;
        """
    )
    op.execute(
        """
        CREATE TRIGGER IF NOT EXISTS trg_world_events_profile_binding_update
        BEFORE UPDATE ON world_events
        WHEN NEW.project_profile_version_id IS NOT NULL
         AND NEW.profile_version IS NOT NULL
         AND NOT EXISTS (
            SELECT 1 FROM project_profile_versions
            WHERE id = NEW.project_profile_version_id
              AND project_id = NEW.project_id
              AND version = NEW.profile_version
         )
        BEGIN
            SELECT RAISE(ABORT, 'world_events profile binding mismatch');
        END;
        """
    )

    op.create_table(
        "world_fact_claims",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("project_profile_version_id", sa.String(), nullable=True),
        sa.Column("profile_version", sa.Integer(), nullable=True),
        sa.Column("claim_id", sa.String(), nullable=False),
        sa.Column("chapter_index", sa.Integer(), nullable=True),
        sa.Column("intra_chapter_seq", sa.Integer(), nullable=True),
        sa.Column("subject_ref", sa.String(), nullable=False),
        sa.Column("predicate", sa.String(), nullable=False),
        sa.Column("object_ref_or_value", sa.JSON(), nullable=False),
        sa.Column("claim_layer", sa.String(), nullable=False),
        sa.Column("claim_status", sa.String(), nullable=False),
        sa.Column("valid_from_anchor_id", sa.String(), nullable=True),
        sa.Column("valid_to_anchor_id", sa.String(), nullable=True),
        sa.Column("source_event_ref", sa.String(), nullable=True),
        sa.Column("evidence_refs", sa.JSON(), nullable=True),
        sa.Column("authority_type", sa.String(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("contract_version", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint("profile_version IS NOT NULL OR project_profile_version_id IS NOT NULL", name="ck_world_fact_claims_has_profile_version_binding"),
        sa.CheckConstraint("authority_type IN ('authoritative_structured', 'derived', 'annotation', 'opaque_blob')", name="ck_world_fact_claims_authority_type"),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_world_fact_claims_confidence_range"),
        sa.ForeignKeyConstraint(["project_id", "profile_version"], ["project_profile_versions.project_id", "project_profile_versions.version"]),
        sa.ForeignKeyConstraint(["project_id", "project_profile_version_id"], ["project_profile_versions.project_id", "project_profile_versions.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "claim_id", name="uq_world_fact_claims_project_claim_id"),
    )
    op.create_index("ix_world_fact_claims_project_profile_version", "world_fact_claims", ["project_id", "profile_version"])
    op.create_index("ix_world_fact_claims_chapter_seq", "world_fact_claims", ["chapter_index", "intra_chapter_seq"])
    op.execute(
        """
        CREATE TRIGGER IF NOT EXISTS trg_world_fact_claims_profile_binding_insert
        BEFORE INSERT ON world_fact_claims
        WHEN NEW.project_profile_version_id IS NOT NULL
         AND NEW.profile_version IS NOT NULL
         AND NOT EXISTS (
            SELECT 1 FROM project_profile_versions
            WHERE id = NEW.project_profile_version_id
              AND project_id = NEW.project_id
              AND version = NEW.profile_version
         )
        BEGIN
            SELECT RAISE(ABORT, 'world_fact_claims profile binding mismatch');
        END;
        """
    )
    op.execute(
        """
        CREATE TRIGGER IF NOT EXISTS trg_world_fact_claims_profile_binding_update
        BEFORE UPDATE ON world_fact_claims
        WHEN NEW.project_profile_version_id IS NOT NULL
         AND NEW.profile_version IS NOT NULL
         AND NOT EXISTS (
            SELECT 1 FROM project_profile_versions
            WHERE id = NEW.project_profile_version_id
              AND project_id = NEW.project_id
              AND version = NEW.profile_version
         )
        BEGIN
            SELECT RAISE(ABORT, 'world_fact_claims profile binding mismatch');
        END;
        """
    )

    op.create_table(
        "world_evidence",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("project_profile_version_id", sa.String(), nullable=True),
        sa.Column("profile_version", sa.Integer(), nullable=True),
        sa.Column("evidence_id", sa.String(), nullable=False),
        sa.Column("chapter_index", sa.Integer(), nullable=True),
        sa.Column("intra_chapter_seq", sa.Integer(), nullable=True),
        sa.Column("evidence_type", sa.String(), nullable=False),
        sa.Column("source_scope", sa.String(), nullable=False),
        sa.Column("content_excerpt_or_summary", sa.Text(), nullable=True),
        sa.Column("holder_ref", sa.String(), nullable=True),
        sa.Column("authenticity_status", sa.String(), nullable=True),
        sa.Column("reliability_level", sa.String(), nullable=True),
        sa.Column("disclosure_layer", sa.String(), nullable=False),
        sa.Column("related_claim_refs", sa.JSON(), nullable=True),
        sa.Column("related_event_refs", sa.JSON(), nullable=True),
        sa.Column("timeline_anchor_id", sa.String(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("contract_version", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint("profile_version IS NOT NULL OR project_profile_version_id IS NOT NULL", name="ck_world_evidence_has_profile_version_binding"),
        sa.ForeignKeyConstraint(["project_id", "profile_version"], ["project_profile_versions.project_id", "project_profile_versions.version"]),
        sa.ForeignKeyConstraint(["project_id", "project_profile_version_id"], ["project_profile_versions.project_id", "project_profile_versions.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "evidence_id", name="uq_world_evidence_project_evidence_id"),
    )
    op.create_index("ix_world_evidence_project_profile_version", "world_evidence", ["project_id", "profile_version"])
    op.create_index("ix_world_evidence_chapter_seq", "world_evidence", ["chapter_index", "intra_chapter_seq"])
    op.create_index("ix_world_evidence_evidence_id", "world_evidence", ["evidence_id"])
    op.execute(
        """
        CREATE TRIGGER IF NOT EXISTS trg_world_evidence_profile_binding_insert
        BEFORE INSERT ON world_evidence
        WHEN NEW.project_profile_version_id IS NOT NULL
         AND NEW.profile_version IS NOT NULL
         AND NOT EXISTS (
            SELECT 1 FROM project_profile_versions
            WHERE id = NEW.project_profile_version_id
              AND project_id = NEW.project_id
              AND version = NEW.profile_version
         )
        BEGIN
            SELECT RAISE(ABORT, 'world_evidence profile binding mismatch');
        END;
        """
    )
    op.execute(
        """
        CREATE TRIGGER IF NOT EXISTS trg_world_evidence_profile_binding_update
        BEFORE UPDATE ON world_evidence
        WHEN NEW.project_profile_version_id IS NOT NULL
         AND NEW.profile_version IS NOT NULL
         AND NOT EXISTS (
            SELECT 1 FROM project_profile_versions
            WHERE id = NEW.project_profile_version_id
              AND project_id = NEW.project_id
              AND version = NEW.profile_version
         )
        BEGIN
            SELECT RAISE(ABORT, 'world_evidence profile binding mismatch');
        END;
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_world_evidence_profile_binding_update")
    op.execute("DROP TRIGGER IF EXISTS trg_world_evidence_profile_binding_insert")
    op.drop_index("ix_world_evidence_evidence_id", table_name="world_evidence")
    op.drop_index("ix_world_evidence_chapter_seq", table_name="world_evidence")
    op.drop_index("ix_world_evidence_project_profile_version", table_name="world_evidence")
    op.drop_table("world_evidence")

    op.execute("DROP TRIGGER IF EXISTS trg_world_fact_claims_profile_binding_update")
    op.execute("DROP TRIGGER IF EXISTS trg_world_fact_claims_profile_binding_insert")
    op.drop_index("ix_world_fact_claims_chapter_seq", table_name="world_fact_claims")
    op.drop_index("ix_world_fact_claims_project_profile_version", table_name="world_fact_claims")
    op.drop_table("world_fact_claims")

    op.execute("DROP TRIGGER IF EXISTS trg_world_events_profile_binding_update")
    op.execute("DROP TRIGGER IF EXISTS trg_world_events_profile_binding_insert")
    op.drop_index("ix_world_events_chapter_seq", table_name="world_events")
    op.drop_index("ix_world_events_project_profile_version", table_name="world_events")
    op.drop_table("world_events")

    op.drop_index("ix_world_timeline_anchors_chapter_seq", table_name="world_timeline_anchors")
    op.drop_index("ix_world_timeline_anchors_anchor_id", table_name="world_timeline_anchors")
    op.drop_index("ix_world_timeline_anchors_project_profile_version", table_name="world_timeline_anchors")
    op.drop_table("world_timeline_anchors")

    op.drop_index("ix_world_relations_relation_id", table_name="world_relations")
    op.drop_index("ix_world_relations_project_profile_version", table_name="world_relations")
    op.drop_table("world_relations")

    op.drop_index("ix_world_resources_primary_alias", table_name="world_resources")
    op.drop_index("ix_world_resources_canonical_id", table_name="world_resources")
    op.drop_index("ix_world_resources_project_profile_version", table_name="world_resources")
    op.drop_table("world_resources")

    op.drop_index("ix_world_rules_primary_alias", table_name="world_rules")
    op.drop_index("ix_world_rules_canonical_id", table_name="world_rules")
    op.drop_index("ix_world_rules_project_profile_version", table_name="world_rules")
    op.drop_table("world_rules")

    op.drop_index("ix_world_artifacts_primary_alias", table_name="world_artifacts")
    op.drop_index("ix_world_artifacts_canonical_id", table_name="world_artifacts")
    op.drop_index("ix_world_artifacts_project_profile_version", table_name="world_artifacts")
    op.drop_table("world_artifacts")

    op.drop_index("ix_world_factions_primary_alias", table_name="world_factions")
    op.drop_index("ix_world_factions_canonical_id", table_name="world_factions")
    op.drop_index("ix_world_factions_project_profile_version", table_name="world_factions")
    op.drop_table("world_factions")

    op.drop_index("ix_world_locations_primary_alias", table_name="world_locations")
    op.drop_index("ix_world_locations_canonical_id", table_name="world_locations")
    op.drop_index("ix_world_locations_project_profile_version", table_name="world_locations")
    op.drop_table("world_locations")

    op.drop_index("ix_world_characters_primary_alias", table_name="world_characters")
    op.drop_index("ix_world_characters_canonical_id", table_name="world_characters")
    op.drop_index("ix_world_characters_project_profile_version", table_name="world_characters")
    op.drop_table("world_characters")

    op.execute("DROP TRIGGER IF EXISTS trg_project_profile_versions_contract_version_insert")
    op.execute("DROP TRIGGER IF EXISTS trg_project_profile_versions_append_only_delete")
    op.execute("DROP TRIGGER IF EXISTS trg_project_profile_versions_append_only")
    op.drop_index("ix_project_profile_versions_project_version", table_name="project_profile_versions")
    op.drop_table("project_profile_versions")

    op.drop_index("ix_genre_profiles_primary_alias", table_name="genre_profiles")
    op.drop_index("ix_genre_profiles_canonical_id", table_name="genre_profiles")
    op.drop_table("genre_profiles")
