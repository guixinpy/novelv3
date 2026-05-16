# Longform Scale Phase 213 - Project Lightweight Current Profile References

## Goal

Avoid loading large `project_profile_versions.profile_payload` JSON in hot Athena routes that only need profile identifiers and version metadata.

## Problem

The shared `get_current_profile()` helper queried full `ProjectProfileVersion` ORM rows. Routes such as Athena chat, ontology, state timeline, and consistency checks use only `id`, `version`, and `contract_version`, but the query also materialized `profile_payload`.

For long projects, profile payloads can grow with contract metadata and structured world-model context, making this an avoidable cost on common navigation and write paths.

## Change

- Added `CurrentProfileRef`, a lightweight frozen dataclass.
- `get_current_profile()` now selects only:
  - `id`
  - `project_id`
  - `version`
  - `contract_version`
- `create_dialog_world_update_proposal()` now accepts the lightweight profile reference.

## Regression Test

- `test_athena_ontology_current_profile_lookup_skips_profile_payload` verifies profiled ontology requests do not select `profile_payload`.

## Verification

Initial verification:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_world_frontend_api.py::test_athena_ontology_current_profile_lookup_skips_profile_payload -q
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_world_frontend_api.py -q
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_athena_dialog.py backend/tests/test_consistency.py -q
```

Results:

- Regression test: `1 passed`
- World frontend API tests: `39 passed`
- Athena dialog and consistency tests: `31 passed`

Full verification is run before commit.
