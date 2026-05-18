# Longform Scale Phase 277 - Retarget Writing State Reconciliation

## Objective

Keep writing state consistent when the project target chapter count changes. A long-running project may be replanned: shortening the target should stop further writing, while extending the target should reopen a previously completed writing pointer.

## Scope

- Added `WritingStateService.reconcile_target()`.
- When `target_chapter_count` is updated through `PATCH /projects/{project_id}`, the writing state is reconciled against the shared effective target guard.
- If the current pointer is beyond the new target, status becomes `completed`.
- If the state was `completed` but the new target now includes the current pointer, status becomes `idle`.
- Other statuses are left unchanged when the target still includes the pointer.

## TDD Evidence

- RED: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_projects.py -q -k "target and writing"`
  - Failed because shortening target left state `running`, and extending target left state `completed`.
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_projects.py -q -k "target and writing"`
  - `2 passed, 10 deselected`.
- Related regression: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_projects.py backend\tests\test_writing.py backend\tests\test_chapters.py -q`
  - `59 passed`.

## Full Verification

- `backend\.venv\Scripts\python.exe -m pytest backend\tests -q`
  - `670 passed in 57.53s`.
- `npm run build` in `frontend`
  - Passed (`vue-tsc --noEmit && vite build`).
- `npm run test:unit -- --run` in `frontend`
  - `64 passed`; `432 passed`.
- `git diff --check`
  - Passed.
- DeepSeek key scan
  - `NO_MATCH`.
