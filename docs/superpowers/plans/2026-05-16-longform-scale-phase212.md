# Longform Scale Phase 212 - Skip Setup JSON In Profiled Ontology

## Goal

Keep Athena catalog/ontology loading lightweight after a project has already imported Setup into the world model.

## Problem

`GET /athena/ontology` queried the full `Setup` row even when a current world-model profile existed. At that stage the response is driven by structured ontology tables, and the frontend only needs `setup_summary` to decide whether setup import is available before profile creation.

For long projects, Setup can contain large character lists, world-building JSON, and core concept payloads. Reading it on every ontology refresh creates avoidable database and JSON materialization cost.

## Change

- `get_ontology()` now reads `Setup` only when no current profile exists.
- When a profile exists, `setup_summary` is returned as `null`.
- Existing fallback behavior for pre-import projects remains unchanged.

## Regression Test

- `test_athena_ontology_with_profile_does_not_select_setup_json` verifies:
  - profiled ontology still returns structured entities;
  - `setup_summary` is `null`;
  - the request does not query the `setups` table.

## Verification

Initial verification:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_world_frontend_api.py::test_athena_ontology_with_profile_does_not_select_setup_json -q
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_world_frontend_api.py -q
```

Results:

- Regression test: `1 passed`
- World frontend API tests: `38 passed`

Full verification is run before commit.
