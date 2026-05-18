# Longform Scale Phase 263 - Hermes Writing Progress Visibility

## Goal

Make the persisted writing state visible in the Hermes workspace sidebar after cold start. A thousand-chapter project must show the current writing chapter and failure state immediately after reload.

## Scope

- Add writing progress display to `ProjectDashboard`.
- Pass `project.writingState` from `HermesView` into the dashboard.
- Keep the UI read-only and compact.

## RED

- `npm run test:unit -- --run src/components/shared/ProjectDashboard.test.ts -t "writing progress"`
  - Failed because the dashboard did not render `写作进度`.

## GREEN

- `npm run test:unit -- --run src/components/shared/ProjectDashboard.test.ts -t "writing progress"`
  - `1 passed`, `6 skipped`

## Related Verification

- `npm run test:unit -- --run src/components/shared/ProjectDashboard.test.ts`
  - `7 passed`
- `npm run test:unit -- --run src/views/ManuscriptView.test.ts src/views/AthenaView.test.ts src/stores/project.workspace.test.ts`
  - `3 passed`, `36 passed`

## Full Verification

- `backend\.venv\Scripts\python.exe -m pytest backend\tests -q`
  - `654 passed`
- `npm run build`
  - `vue-tsc --noEmit && vite build` passed
- `npm run test:unit -- --run`
  - `62 passed`, `422 passed`
- `git diff --check`
  - Passed
- DeepSeek key scan
  - `NO_MATCH`
