# Longform Scale Phase 288 - Preserve Forward Writing Pointer On Old Chapter Retry

## Objective

Prevent retrying or regenerating an older chapter from moving the next writing pointer backward. In long projects, retrying chapter 2 must not reset `current_chapter` from 100 to 2 or 3.

## Scope

- `WritingStateService.run_chapter()` now keeps `current_chapter` at the maximum of the existing pointer and the requested chapter.
- Added regression coverage for queuing an old chapter retry and for successful old-chapter retry work.

## TDD Evidence

- RED: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing.py -q -k "pointer"`
  - Failed because retrying chapter 2 returned `current_chapter=2` after the pointer had reached 100.
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing.py -q -k "pointer or retry_creates_background_task or retry_chapter_work_marks_state_idle"`
  - `4 passed, 15 deselected`.
- Related regression: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing.py backend\tests\test_chapters.py backend\tests\test_projects.py -q`
  - `66 passed in 5.13s`.

## Full Verification

- `backend\.venv\Scripts\python.exe -m pytest backend\tests -q`
  - `681 passed in 62.63s`.
- `npm run build` in `frontend`
  - Passed.
- `npm run test:unit -- --run` in `frontend`
  - `64 passed`; `435 passed`.
- `git diff --check`
  - Passed.
- DeepSeek key scan
  - `NO_MATCH`.
