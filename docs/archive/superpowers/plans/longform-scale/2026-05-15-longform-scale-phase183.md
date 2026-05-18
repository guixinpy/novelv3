# Phase 183 - Add World Projection Hot Indexes

## Problem

World projection reads filter by project/profile and then order facts, events, and
anchors by chapter sequence. The tables had profile or chapter indexes separately,
but not compound indexes aligned with those projection source queries.

## Change

- Added `ix_world_timeline_anchors_project_profile_order` for ordered anchor reads.
- Added `ix_world_events_project_profile_order` for ordered event reads within a
  project profile.
- Added `ix_world_fact_claims_project_profile_status_order` for confirmed/truth
  fact reads and ordered projection materialization.
- Added an Alembic migration for existing local databases.

## Tests

- RED: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_longform_hot_tables_have_query_indexes -q`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_longform_hot_tables_have_query_indexes -q`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_world_frontend_api.py::test_athena_timeline_endpoint_uses_current_world_event_fields backend\tests\test_world_frontend_api.py::test_athena_timeline_endpoint_returns_latest_bounded_window backend\tests\test_world_projection_service.py -q`
- GREEN: `.\.venv\Scripts\python.exe -m alembic heads` from `backend`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests -q`
- GREEN: `npm run test:unit` from `frontend`
- GREEN: `npm run build` from `frontend`
- GREEN: `git diff --check`
- GREEN: DeepSeek key scan returned `NO_MATCH`

## Result

Projection source loading now has compound indexes matching longform world-model
read patterns instead of relying on separate profile and chapter indexes.
