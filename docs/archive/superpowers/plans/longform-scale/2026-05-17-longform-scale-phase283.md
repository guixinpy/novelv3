# Longform Scale Phase 283 - Refresh Writing State After Outline Generation

## Objective

Keep frontend writing controls aligned after outline regeneration. The backend now reconciles `writing_state` when outline `total_chapters` changes, so the frontend must reload writing state after `generateOutline()` succeeds.

## Scope

- `generateOutline()` now refreshes `writing_state` after reloading the project.
- The refresh is best-effort, matching direct chapter generation behavior.
- Added a regression test proving outline generation updates the project store's writing state.

## TDD Evidence

- RED: `npm run test:unit -- --run src/stores/project.workspace.test.ts -t "generateOutline"`
  - Failed because `api.getWritingState` was never called after outline generation.
- GREEN: `npm run test:unit -- --run src/stores/project.workspace.test.ts -t "generateOutline"`
  - Passed.
- Related regression: `npm run test:unit -- --run src/stores/project.workspace.test.ts src/views/AthenaView.test.ts src/components/shared/ProjectDashboard.test.ts`
  - `3 passed`; `46 passed`.

## Full Verification

- `backend\.venv\Scripts\python.exe -m pytest backend\tests -q`
  - `678 passed in 65.19s`
- `npm run build` in `frontend`
  - Passed.
- `npm run test:unit -- --run` in `frontend`
  - `64 passed`; `435 passed`.
- `git diff --check`
  - Passed.
- DeepSeek key scan
  - `NO_MATCH`.
