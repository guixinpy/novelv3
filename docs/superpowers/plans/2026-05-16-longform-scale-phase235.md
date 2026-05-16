# Phase 235: Window Athena Consistency Facade

## Goal

Ensure the Athena consistency facade supports bounded issue history windows and does not pass dependency or query marker objects into the lower-level consistency endpoint.

## RED

- `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_consistency.py::test_athena_evolution_consistency_forwards_issue_window -q`
  - Failed because `/athena/evolution/consistency` called `list_issues(project_id, db)`, shifting the database session into `offset` and leaving `db` as a FastAPI dependency marker.

## GREEN

- Added explicit `offset` and `limit` query parameters to the Athena consistency facade.
- Forwarded concrete values to `list_issues()` with keyword arguments.

## Verification

- Targeted backend test passes after implementation.
- Full backend, frontend build, frontend unit tests, whitespace diff check, and key scan are required before commit.
