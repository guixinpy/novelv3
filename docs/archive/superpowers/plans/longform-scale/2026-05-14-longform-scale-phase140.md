# Phase 140 - Writing retry task state closure

## Goal

Close the writing retry task lifecycle so the writing control state does not remain `running` after an async retry finishes or fails.

## Why

In long-form projects, chapter retry tasks may happen while operators are monitoring hundreds or thousands of chapters. A stale `running` state hides completion, blocks reliable retry decisions, and makes failures hard to distinguish from active work.

## TDD

RED:

- `test_retry_chapter_work_marks_state_idle_after_success` expected retry work to return chapter 2 and set writing state to `idle/current_chapter=2`.
- `test_retry_chapter_work_marks_state_failed_after_error` expected retry work failures to set `failed/current_chapter=2/last_error`.
- Both failed because the retry work builder did not exist yet.

GREEN:

- Added `build_retry_chapter_work(project_id, chapter_index)` so retry work can be tested directly.
- Added `WritingStateService.complete_chapter(...)`.
- Retry work now marks state `idle` after success and `failed` on generation errors.
- Retry work now accepts the actual chapter generation API shape, including dictionary responses.

## Verification

- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing.py::test_retry_chapter_work_marks_state_idle_after_success backend\tests\test_writing.py::test_retry_chapter_work_marks_state_failed_after_error -q`
- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing.py -q`
- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_background.py -q`
