# Phase 254 - Background Retry Progress Snapshot

## Goal

Improve long-form background task resumability. When a thousand-chapter range
task fails, the retry task should keep a compact snapshot of the failed task's
progress so operators can see how much work completed and where the retry
resumes, without copying large checkpoint arrays.

## TDD Evidence

- RED:
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_background.py -q -k "retry_keeps_compact_failed_progress_snapshot"`
  - Failed because retry payload did not include `previous_progress`.
- GREEN:
  - Same focused command passed with `1 passed`.
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_background.py -q`
    passed with `26 passed`.

## Changes

- `create_retry_from_failed()` now stores `previous_progress` in the retry
  payload.
- The snapshot excludes `completed_chapter_indexes` and records
  `checkpoint_count` instead, keeping retry payloads bounded for thousand-chapter
  tasks.
- Existing `resume_from_chapter_index` behavior is unchanged.

## Verification Evidence

Fresh verification before committing this phase:

- `backend\.venv\Scripts\python.exe -m pytest backend/tests -q` passed with `648 passed`.
- `npm run build` passed.
- `npm run test:unit -- --run` passed with `418 passed`.
- `git diff --check` passed.
- DeepSeek key scan returned `NO_MATCH`.
