# Longform Scale Phase 299 - Keep Active Task Lookup Lightweight

## Goal

Keep writing-state recovery fast as background task history grows in long projects.

## Finding

Phase 298 added active writing task recovery, but the lookup selected full `BackgroundTask` rows. That could pull heavy `result` and `error` payloads just to recover a `task_id`. The table also lacked a composite index for `project_id + task_type + status + created_at`, which is the shape of the active task lookup.

## TDD Evidence

RED:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing.py::test_writing_state_active_task_lookup_does_not_select_heavy_task_fields -q
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_longform_hot_tables_have_query_indexes -q
```

Observed failures:

```text
background_tasks.result selected during active task lookup
ix_background_tasks_project_type_status_created missing
```

GREEN:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing.py::test_writing_state_active_task_lookup_does_not_select_heavy_task_fields -q
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_longform_hot_tables_have_query_indexes -q
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_world_profiles.py::test_migration_upgrade_enforces_trigger_and_foreign_keys -q
```

Observed result:

```text
1 passed
1 passed
1 passed
```

## Change

- Added `ix_background_tasks_project_type_status_created`.
- Added an Alembic migration for the new index.
- Changed active writing task lookup to select only `id`, `task_type`, and `payload`.

## Verification

Full phase gate passed:

- `backend\.venv\Scripts\python.exe -m alembic heads` - one head
- `backend\.venv\Scripts\python.exe -m pytest backend\tests -q` - 690 passed
- `npm run build` - passed
- `npm run test:unit -- --run` - 440 passed
- `git diff --check` - passed
- DeepSeek key scan - `NO_MATCH`
