# Phase 231: Bound World Projection Cache Size

## Goal

Avoid retaining oversized world-model projections in the process-local LRU cache for long-running large projects.

## Verification

- RED: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_world_projection_service.py::test_projection_service_skips_local_cache_for_oversized_projection -q`
  - Failed because there was no projection item-count cache gate.
- GREEN: same targeted test passes after adding `WORLD_PROJECTION_CACHE_MAX_ITEMS`.

## Notes

- Small projections still reuse the local cache.
- Oversized projections are returned to the caller but not retained in `_projection_cache`.
- This controls retained process memory; projection construction itself remains a separate optimization target.
