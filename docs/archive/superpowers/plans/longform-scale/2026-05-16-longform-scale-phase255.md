# Phase 255 - Background Range Pending Chapter Helper

## Goal

Provide a single service-level way to compute which chapters remain for a range
background task. This is a foundation for resumable thousand-chapter maintenance
or indexing runners, so they do not each reimplement checkpoint logic.

## TDD Evidence

- RED:
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_background.py -q -k "pending_chapter_indexes"`
  - Failed because `BackgroundTaskService` did not expose
    `pending_chapter_indexes`.
- GREEN:
  - Same focused command passed with `2 passed`.
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_background.py -q`
    passed with `28 passed`.

## Changes

- Added `BackgroundTaskService.pending_chapter_indexes(task_id)`.
- The helper skips sparse completed checkpoints for active/original tasks.
- For retry tasks without their own result progress, the helper starts from
  `resume_from_chapter_index`.

## Verification Evidence

Fresh verification before committing this phase:

- `backend\.venv\Scripts\python.exe -m pytest backend/tests -q` passed with `650 passed`.
- `npm run build` passed.
- `npm run test:unit -- --run` passed with `418 passed`.
- `git diff --check` passed.
- DeepSeek key scan returned `NO_MATCH`.
