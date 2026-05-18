# Longform Scale Phase 268 - Hermes Writing Controls

## Goal

Make the persisted writing state actionable in Hermes. A longform writer should be able to start, pause, resume, or retry the current writing session from the same sidebar that shows the current chapter.

## Scope

- Add a compact writing control button to `ProjectDashboard`.
- Map writing statuses to control actions:
  - `idle` -> start
  - `running` -> pause
  - `paused` -> resume
  - `failed` -> start/retry
- Wire the dashboard control through `HermesView` to the project store writing actions.

## RED

- `npm run test:unit -- --run src/components/shared/ProjectDashboard.test.ts -t "writing control"`
  - Failed because the dashboard rendered writing progress but no `dashboard-writing-control` button.
- `npm run test:unit -- --run src/views/HermesView.test.ts -t "starts writing"`
  - Failed because clicking the dashboard control emitted no Hermes action and `api.startWriting` was not called.

## GREEN

- `npm run test:unit -- --run src/components/shared/ProjectDashboard.test.ts -t "writing control"`
  - `1 passed`, `7 skipped`
- `npm run test:unit -- --run src/views/HermesView.test.ts -t "starts writing"`
  - `1 passed`

## Related Verification

- `npm run test:unit -- --run src/components/shared/ProjectDashboard.test.ts src/views/HermesView.test.ts src/stores/project.workspace.test.ts`
  - `33 passed`

## Full Verification

- `backend\.venv\Scripts\python.exe -m pytest backend\tests -q`
  - `657 passed`
- `npm run build`
  - `vue-tsc --noEmit && vite build` passed
- `npm run test:unit -- --run`
  - `64 passed`, `429 passed`
- `git diff --check`
  - Passed
- DeepSeek key scan
  - `NO_MATCH`
