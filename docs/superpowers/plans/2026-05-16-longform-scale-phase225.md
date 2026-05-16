# Phase 225: Window Topology Nodes And Edges

## Goal

Avoid loading the full topology node and edge JSON arrays when the main topology endpoint only needs a bounded page.

## Verification

- RED: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_topologies.py::test_existing_topology_window_does_not_select_full_node_or_edge_json -q`
  - Failed because the endpoint did not use `json_each(topologies.nodes)` or `json_each(topologies.edges)` for windowed reads.
- GREEN: same targeted test passes after moving node and edge pages to database-side `json_each(... LIMIT/OFFSET)` queries.

## Notes

- `GET /api/v1/projects/{project_id}/topology` now reads topology metadata and totals without selecting the full `nodes` or `edges` columns.
- Existing topology creation behavior is unchanged; missing topologies are still built on demand.
- Character graph and timeline endpoints still use the full topology because they filter by node and edge semantics; those remain separate optimization targets.
