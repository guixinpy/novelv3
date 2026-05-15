# Phase 178 - Bulk Fail Interrupted Background Tasks

## Problem

`BackgroundTaskService.fail_interrupted_running_tasks` loaded every pending and
running `BackgroundTask` row before marking restart-interrupted tasks as failed.
For longform projects this can deserialize large `payload`, `result`, and `error`
fields during app startup, exactly when the system should recover quickly.

## Change

- Replaced per-row loading and mutation with one bulk `UPDATE` for active task
  statuses.
- Preserved the existing behavior: pending and running tasks become failed with
  the restart interruption error and a shared `finished_at` timestamp.
- Added a SQL regression test that captures the restart path and rejects any
  `SELECT ... FROM background_tasks` during the bulk failure step.

## Tests

- RED: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_background.py::test_background_task_service_fails_interrupted_tasks_without_selecting_rows -q`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_background.py::test_background_task_service_fails_interrupted_tasks_without_selecting_rows -q`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_background.py -q`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests -q`
- GREEN: `npm run test:unit` from `frontend`
- GREEN: `npm run build` from `frontend`
- GREEN: `git diff --check`
- GREEN: DeepSeek key scan returned `NO_MATCH`

## Result

Task restart recovery is no longer proportional to the serialized size of active
task rows, reducing startup memory pressure for thousand-chapter workflows.
