# Longform Scale Phase 287 - Completed Writing Progress Label

## Objective

Avoid showing the next writing pointer as if it were a real chapter after a project reaches its target. For a 100-chapter project, completed state may store `current_chapter=101`; the dashboard should show completion, not "第101章".

## Scope

- Project dashboard now displays `全部章节` when `writingState.status === "completed"`.
- Added a regression assertion that completed writing state does not show the next pointer chapter.

## TDD Evidence

- RED: `npm run test:unit -- --run src/components/shared/ProjectDashboard.test.ts -t "completed writing state"`
  - Failed because the title was `写作进度 · 第101章`.
- GREEN: same command
  - `1 passed`, `8 skipped`.
- Related regression: `npm run test:unit -- --run src/components/shared/ProjectDashboard.test.ts src/views/HermesView.test.ts src/views/ProjectListView.test.ts`
  - `3 passed`; `14 passed`.

## Full Verification

- `backend\.venv\Scripts\python.exe -m pytest backend\tests -q`
  - `679 passed in 66.25s`.
- `npm run build` in `frontend`
  - Passed.
- `npm run test:unit -- --run` in `frontend`
  - `64 passed`; `435 passed`.
- `git diff --check`
  - Passed.
- DeepSeek key scan
  - `NO_MATCH`.
