# Longform Scale Phase 282 - Long Writing Task Polling

## Objective

Keep the UI synchronized for slow long-form chapter generation. A single network-novel chapter can take longer than 60 seconds when the model is slow, the prompt is large, or a retry is running. The writing task poller should not silently stop before the task reaches a terminal state.

## Scope

- Increased the writing task poll window from 60 seconds to 30 minutes.
- Kept the existing one-second polling interval and project-scope cancellation checks.
- Added a fake-timer regression test for a task that completes on poll 61.

## TDD Evidence

- RED: `npm run test:unit -- --run src/stores/project.workspace.test.ts -t "超过 60 秒"`
  - Failed because the poller stopped at 60 calls and never refreshed `writing_state`.
- GREEN: `npm run test:unit -- --run src/stores/project.workspace.test.ts -t "超过 60 秒"`
  - Passed.
- Related regression: `npm run test:unit -- --run src/stores/project.workspace.test.ts src/components/shared/ProjectDashboard.test.ts src/views/HermesView.test.ts`
  - `3 passed`; `37 passed`.

## Full Verification

- `backend\.venv\Scripts\python.exe -m pytest backend\tests -q`
  - `678 passed in 60.38s`.
- `npm run build` in `frontend`
  - Passed (`vue-tsc --noEmit && vite build`).
- `npm run test:unit -- --run` in `frontend`
  - `64 passed`; `434 passed`.
- `git diff --check`
  - Passed.
- DeepSeek key scan
  - `NO_MATCH`.
