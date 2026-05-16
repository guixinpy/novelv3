# Phase 233: Window Athena Character Graph Facade

## Goal

Expose node and edge pagination through the Athena character graph facade and frontend client, so large character topology graphs can be requested in bounded windows instead of relying on default payloads.

## RED

- `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_topologies.py::test_athena_ontology_character_graph_forwards_window_params -q`
  - Failed because the Athena facade called the topology route with FastAPI `Query` defaults instead of concrete window values.
- `npm run test:unit -- --run src/api/client.worldModel.test.ts`
  - Failed because `getAthenaCharacterGraph()` ignored window params and emitted the bare endpoint URL.

## GREEN

- Added explicit `node_offset`, `node_limit`, `edge_offset`, and `edge_limit` parameters to `/athena/ontology/character-graph`.
- Forwarded concrete values to the underlying topology character graph function.
- Added `AthenaTopologyWindowQuery` and frontend query serialization for `getAthenaCharacterGraph()`.

## Verification

- Targeted backend and frontend tests pass after implementation.
- Full backend, frontend build, frontend unit tests, whitespace diff check, and key scan are required before commit.
