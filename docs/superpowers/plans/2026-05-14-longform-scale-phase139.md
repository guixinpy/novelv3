# Phase 139 - Writing retry state feedback

## Goal

Make chapter retry control-plane feedback reflect the active retry chapter, instead of returning the default idle state after a retry task is queued.

## Why

For thousand-chapter writing sessions, operators need to know which chapter is currently being retried. Returning `idle/current_chapter=1` after queuing chapter `N` hides active work and makes retry/resume decisions unreliable.

## TDD

RED:

- `backend/tests/test_writing.py::test_writing_retry_creates_background_task` expected retrying chapter 2 to return `status=running` and `current_chapter=2`.
- It failed with `status=idle`.

GREEN:

- Added `WritingStateService.run_chapter(project_id, chapter_index)`.
- Exposed it through `WritingScheduler`.
- `retry_chapter` now returns that running chapter state after starting the background retry task.

## Verification

- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing.py::test_writing_retry_creates_background_task -q`
- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing.py -q`
- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_background.py -q`
