# Phase 234: Window Athena Topology Timeline Facade

## Goal

Expose bounded `offset` and `limit` parameters through the Athena topology timeline facade, keeping the large topology timeline path safe for long projects.

## RED

- `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_topologies.py::test_athena_ontology_topology_timeline_forwards_window_params -q`
  - Failed because the facade called the underlying timeline route with FastAPI `Query` defaults, which reached SQL as unsupported bind values.

## GREEN

- Added explicit `offset` and `limit` query parameters to `/athena/ontology/topology-timeline`.
- Forwarded concrete values to the underlying topology timeline function with keyword arguments.

## Verification

- Targeted backend test passes after implementation.
- Full backend, frontend build, frontend unit tests, whitespace diff check, and key scan are required before commit.
