# Longform Scale Phase 284 - Sync Project Completion Status

## Objective

Keep the project-level lifecycle aligned with the writing lifecycle. When the final target chapter is complete, the project should no longer remain in `writing` or `draft`; when the target is extended, a completed project should reopen to a writable state.

## Scope

- `WritingStateService.complete_chapter()` now marks the project `completed` when the next writing pointer exceeds the effective target.
- `WritingStateService.reconcile_target()` now syncs `projects.status/current_phase` when target changes complete or reopen writing.
- Non-final chapter generation keeps the existing `writing` status path unchanged.

## TDD Evidence

- RED: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_chapters.py backend\tests\test_projects.py -q -k "final_project_target or final_outline_target or update_project_target"`
  - Failed because project status stayed `writing` or `draft` while writing state became `completed` or reopened.
- GREEN: same command
  - `4 passed, 43 deselected`.
- Related regression: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_chapters.py backend\tests\test_writing.py backend\tests\test_projects.py -q`
  - `64 passed in 5.52s`.

## Full Verification

- `backend\.venv\Scripts\python.exe -m pytest backend\tests -q`
  - `678 passed in 62.07s`.
- `npm run build` in `frontend`
  - Passed.
- `npm run test:unit -- --run` in `frontend`
  - `64 passed`; `435 passed`.
- `git diff --check`
  - Passed.
- DeepSeek key scan
  - `NO_MATCH`.
