from sqlalchemy import DDL, event


def attach_profile_binding_consistency_triggers(table, table_name: str) -> None:
    create_trigger = DDL(
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
    update_trigger = DDL(
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
    drop_insert_trigger = DDL(f"DROP TRIGGER IF EXISTS trg_{table_name}_profile_binding_insert")
    drop_update_trigger = DDL(f"DROP TRIGGER IF EXISTS trg_{table_name}_profile_binding_update")

    event.listen(
        table,
        "after_create",
        create_trigger.execute_if(dialect="sqlite"),
    )
    event.listen(
        table,
        "after_create",
        update_trigger.execute_if(dialect="sqlite"),
    )
    event.listen(
        table,
        "before_drop",
        drop_insert_trigger.execute_if(dialect="sqlite"),
    )
    event.listen(
        table,
        "before_drop",
        drop_update_trigger.execute_if(dialect="sqlite"),
    )


def attach_parent_item_lineage_consistency_triggers(table, table_name: str, *, bundle_table_name: str) -> None:
    create_insert_trigger = DDL(
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
    create_update_trigger = DDL(
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
    drop_insert_trigger = DDL(f"DROP TRIGGER IF EXISTS trg_{table_name}_parent_item_lineage_insert")
    drop_update_trigger = DDL(f"DROP TRIGGER IF EXISTS trg_{table_name}_parent_item_lineage_update")

    event.listen(
        table,
        "after_create",
        create_insert_trigger.execute_if(dialect="sqlite"),
    )
    event.listen(
        table,
        "after_create",
        create_update_trigger.execute_if(dialect="sqlite"),
    )
    event.listen(
        table,
        "before_drop",
        drop_insert_trigger.execute_if(dialect="sqlite"),
    )
    event.listen(
        table,
        "before_drop",
        drop_update_trigger.execute_if(dialect="sqlite"),
    )
