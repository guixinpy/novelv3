# Longform Scale Phase 285 - Delete Writing State With Project

## Objective

Prevent long-running use and repeated scale smoke runs from leaving orphaned writing state rows after a project is deleted.

## Scope

- Added `WritingState` to the project-scoped deletion model list.
- Extended the project cascade-delete regression test to seed and verify writing-state cleanup.

## TDD Evidence

- RED: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_projects.py -q -k "cleans_related_records"`
  - Failed with a SQLite foreign-key error when a project had a `writing_states` row.
- GREEN: same command
  - `1 passed, 11 deselected`.
- Related regression: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_projects.py -q`
  - `12 passed in 0.92s`.

## Full Verification

- `backend\.venv\Scripts\python.exe -m pytest backend\tests -q`
  - `678 passed in 64.31s`.
- `npm run build` in `frontend`
  - Passed.
- `npm run test:unit -- --run` in `frontend`
  - `64 passed`; `435 passed`.
- `git diff --check`
  - Passed.
- DeepSeek key scan
  - `NO_MATCH`.
