# Longform Scale Phase 85: Bounded Ontology Payloads

## Goal

Keep Athena ontology bootstrap usable as a novel grows into hundreds of characters, locations, relations, and rules. The primary `/athena/ontology` response must no longer require loading every world-model row into the frontend in one request.

## Change

- Added bounded query parameters to `/athena/ontology`:
  - `entity_offset`, `entity_limit`
  - `relation_offset`, `relation_limit`
  - `rule_offset`, `rule_limit`
- Added pagination metadata under `pagination.entities`, `pagination.relations`, and `pagination.rules`.
- Kept existing `entities`, `relations`, `rules`, `setup_summary`, and `profile_version` fields compatible.
- Added frontend TypeScript metadata fields for the new response shape.

## Verification

- Red: `python -m pytest backend/tests/test_world_frontend_api.py -k "bounded_world_model_windows" -q --basetemp .tmp/pytest`
- Green: `python -m pytest backend/tests/test_world_frontend_api.py -k "bounded_world_model_windows" -q --basetemp .tmp/pytest`
- API suite: `python -m pytest backend/tests/test_world_frontend_api.py -q --basetemp .tmp/pytest`
