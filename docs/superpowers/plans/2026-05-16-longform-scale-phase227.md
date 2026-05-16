# Phase 227: Window Topology Timeline Events

## Goal

Avoid loading the full topology graph when the timeline endpoint only needs a bounded page of event nodes sorted by chapter index.

## Verification

- RED: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_topologies.py::test_timeline_window_does_not_select_full_topology_json -q`
  - Failed because the endpoint did not use `json_each(topologies.nodes)` for event-window reads.
- GREEN: same targeted test passes after moving event filtering, chapter sorting, and pagination to database-side JSON queries.

## Notes

- `GET /api/v1/projects/{project_id}/topology/timeline` now counts and windows only `EVENT` nodes.
- Sorting remains based on `meta.chapter_index`, with original JSON order as a tie-breaker.
