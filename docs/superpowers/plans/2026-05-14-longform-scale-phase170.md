# Longform Scale Phase 170 - Legacy Ontology Auxiliary Endpoint Bounds

## Problem

The main Athena ontology endpoint already supports bounded world-model windows, but legacy auxiliary endpoints still returned full data:

- `GET /athena/ontology/entities`
- `GET /athena/ontology/rules`

These compatibility endpoints can still be used by older UI paths or integrations, so they should not silently return unbounded payloads in thousand-chapter projects.

## Change

- Added `entity_offset` and `entity_limit` query bounds to `/athena/ontology/entities`.
- Added per-entity-type pagination metadata under `pagination.entities`.
- Added deterministic ordering for entity windows.
- Added `offset` and `limit` query bounds to `/athena/ontology/rules`.
- Added deterministic rule ordering before slicing.

## Tests

Red failure confirmed before implementation:

- The new auxiliary endpoint test requested a middle window but received all entities.

Verification after implementation:

- `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_world_frontend_api.py::test_legacy_athena_ontology_auxiliary_endpoints_are_bounded -q`
- `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_world_frontend_api.py -q`
- `backend\.venv\Scripts\python.exe -m pytest backend\tests -q`

## Result

Legacy ontology helper endpoints now stay bounded by default and support explicit windows. This reduces accidental large payloads from older API paths while keeping the old top-level response keys compatible.
