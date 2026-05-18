# Phase 175 - Filter Projection Facts at Source

## Problem

World projections only materialize confirmed facts, but the projection source query
still loaded every `WorldFactClaim` row for the active profile and filtered
unconfirmed rows in Python. In long-running projects with many obsolete or
non-confirmed claim rows, that added avoidable database IO and Python memory work.

## Change

- Added a SQL-level `claim_status == "confirmed"` filter to the world projection
  fact source query.
- Kept projection output semantics unchanged because current truth, subject
  knowledge, and chapter snapshot projections already ignored unconfirmed facts.

## Tests

- RED: `backend/tests/test_world_projection_service.py::test_projection_source_filters_unconfirmed_fact_rows_in_sql`
- GREEN: target SQL-filter test
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_world_projection_service.py -q`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_world_frontend_api.py -q`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests -q`
- GREEN: `npm run test:unit` from `frontend`
- GREEN: `npm run build` from `frontend`
- GREEN: `git diff --check`
- GREEN: DeepSeek key scan returned `NO_MATCH`

## Result

The world projection path now avoids loading unconfirmed fact rows before building
current truth and related projection views.
