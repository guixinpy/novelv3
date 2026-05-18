# Phase 179 - Source-Filter Background Task Idempotency

## Problem

`BackgroundTaskService.create_chapter_range` reused active range tasks by loading
all active tasks for a project and task type, then checking `payload.idempotency_key`
in Python. For longform workflows with many queued chapter-range jobs this makes
task creation proportional to unrelated active task payloads.

## Change

- Added a SQL regression test that requires the idempotency lookup to include a
  JSON payload condition and `LIMIT`.
- Replaced the Python loop with a source-filtered query on
  `payload["idempotency_key"]`.
- Preserved existing behavior: only active tasks for the same project, task type,
  and idempotency key are reused.

## Tests

- RED: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_background.py::test_background_task_service_filters_idempotency_key_at_source -q`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_background.py::test_background_task_service_filters_idempotency_key_at_source -q`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_background.py -q`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests -q`
- GREEN: `npm run test:unit` from `frontend`
- GREEN: `npm run build` from `frontend`
- GREEN: `git diff --check`
- GREEN: DeepSeek key scan returned `NO_MATCH`

## Result

Range-task idempotency checks no longer materialize every unrelated active task
payload before deciding whether to reuse an existing job.
