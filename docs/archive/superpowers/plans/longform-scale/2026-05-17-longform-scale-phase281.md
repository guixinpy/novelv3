# Longform Scale Phase 281 - Preserve Chapter Window Refresh

## Objective

Keep chapter-list refreshes stable for thousand-chapter projects. When a background writing task finishes while the user is viewing a later chapter window, refreshing `content` should keep the current window instead of jumping back to the first page.

## Scope

- Added current chapter-window refresh parameters in the project store.
- `refreshTargets('content')` now calls `loadChapters(..., force=true, currentWindowParams)` when a window is known.
- Added a regression test for refreshing a window starting at offset `800`.

## TDD Evidence

- RED: `npm run test:unit -- --run src/stores/project.workspace.test.ts -t "非零章节窗口"`
  - Failed because `api.listChapters` was called with `undefined` instead of `{ offset: 800, limit: 50 }`.
- GREEN: `npm run test:unit -- --run src/stores/project.workspace.test.ts -t "非零章节窗口"`
  - Passed with the new test active.
- Related regression: `npm run test:unit -- --run src/stores/project.workspace.test.ts src/views/AthenaView.test.ts src/components/shared/ProjectDashboard.test.ts`
  - `3 passed`; `44 passed`.

## Full Verification

- `backend\.venv\Scripts\python.exe -m pytest backend\tests -q`
  - `678 passed in 63.02s`.
- `npm run build` in `frontend`
  - Passed (`vue-tsc --noEmit && vite build`).
- `npm run test:unit -- --run` in `frontend`
  - `64 passed`; `433 passed`.
- `git diff --check`
  - Passed.
- DeepSeek key scan
  - `NO_MATCH`.
