# Phase 232: Project World Projection Source Fields

## Goal

Avoid selecting unused world-model source columns when building replay projections for large projects.

## Verification

- RED: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_world_projection_service.py::test_projection_source_projects_only_replay_fields -q`
  - Failed because projection source queries selected unused event, fact, anchor, and catalog columns.
- GREEN: same targeted test passes after applying `load_only()` to projection source queries.

## Notes

- Event replay now loads only ids, ordering fields, payload, idempotency, supersession, and anchor references.
- Fact projection now loads only fact-record fields.
- Catalog entity events now load only canonical id and the fields used to build projection attributes.
