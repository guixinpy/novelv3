# Phase 226: Window Character Graph Topology

## Goal

Avoid loading full topology JSON arrays when the character graph endpoint only needs character nodes and relationship or appearance edges.

## Verification

- RED: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_topologies.py::test_character_graph_window_does_not_select_full_topology_json -q`
  - Failed because the endpoint did not use `json_each(topologies.nodes)` or `json_each(topologies.edges)` for filtered windows.
- GREEN: same targeted test passes after moving character-node and graph-edge filtering to database-side JSON queries.

## Notes

- `GET /api/v1/projects/{project_id}/topology/character-graph` now counts and windows filtered topology items without selecting full `nodes` or `edges`.
- The endpoint still creates a missing topology on demand before querying the filtered window.
