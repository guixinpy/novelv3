# Longform Scale Phase 172 - Bounded Legacy Topology Windows

## Problem

Hermes can still request legacy topology data through `project.loadTopology()`.
Those endpoints returned every topology node and edge in one response, which can become a large payload for long-running projects.

Affected paths:

- `GET /api/v1/projects/{project_id}/topology`
- `GET /api/v1/projects/{project_id}/athena/ontology/relations`
- `GET /api/v1/projects/{project_id}/topology/character-graph`
- `GET /api/v1/projects/{project_id}/topology/timeline`

## Change

- Added default topology windows:
  - `node_limit=200`
  - `edge_limit=500`
- Added topology pagination metadata:
  - `nodes_total`, `nodes_offset`, `nodes_limit`, `nodes_has_more`
  - `edges_total`, `edges_offset`, `edges_limit`, `edges_has_more`
- Added explicit window query support to the Athena legacy relations endpoint.
- Bounded `character-graph` and topology timeline helper responses.
- Frontend `api.getTopology()` now serializes topology window params.
- Project store now requests a bounded topology window by default.

## Tests

Red failures confirmed before implementation:

- Backend topology endpoint returned all 250 nodes and 620 edges instead of the expected default window.
- Frontend project store called `api.getTopology(id)` without window params.

Verification after implementation:

- `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_topologies.py::test_topology_endpoints_return_bounded_windows -q`
- `npm run test:unit -- project.workspace`
- `backend\.venv\Scripts\python.exe -m pytest backend\tests -q`
- `npm run test:unit`
- `npm run build`

## Result

Legacy topology paths no longer default to full graph payloads. This keeps older Hermes topology refreshes aligned with the project's thousand-chapter local-view strategy.
