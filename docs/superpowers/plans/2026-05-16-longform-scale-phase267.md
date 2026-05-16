# Longform Scale Phase 267 - Refresh Writing State After Chapter Tasks

## Goal

When a `generate_chapter` background/dialog task completes, all clients that process refresh targets should reload `writing_state` together with project content. This keeps the Hermes writing controls aligned after asynchronous chapter generation.

## Scope

- Add `writing_state` to backend `generate_chapter` refresh targets.
- Add `writing_state` to frontend action refresh targets and `RefreshTarget`.
- Teach the project store to handle `refreshTargets(..., ["writing_state"])`.

## RED

- `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_background.py -q -k "generate_chapter_refreshes_writing_state"`
  - Failed because `refresh_targets` returned `["project", "content", "versions"]` and missed `writing_state`.
- `npm run test:unit -- --run src/components/workspace/workspaceMeta.test.ts`
  - Failed because `getActionRefreshTargets("generate_chapter", "completed")` missed `writing_state`.
- `npm run test:unit -- --run src/stores/project.workspace.test.ts -t "refreshTargets\(writing_state\)"`
  - Failed because `refreshTargets` ignored `writing_state` and returned `[]`.

## GREEN

- `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_background.py -q -k "generate_chapter_refreshes_writing_state"`
  - `1 passed`, `29 deselected`
- `npm run test:unit -- --run src/components/workspace/workspaceMeta.test.ts`
  - `1 passed`
- `npm run test:unit -- --run src/stores/project.workspace.test.ts -t "refreshTargets\(writing_state\)"`
  - `1 passed`, `23 skipped`

## Related Verification

- `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_background.py -q`
  - `30 passed`
- `npm run test:unit -- --run src/components/workspace/workspaceMeta.test.ts src/stores/project.workspace.test.ts`
  - `25 passed`

## Full Verification

- `backend\.venv\Scripts\python.exe -m pytest backend\tests -q`
  - `657 passed`
- `npm run build`
  - `vue-tsc --noEmit && vite build` passed
- `npm run test:unit -- --run`
  - `63 passed`, `427 passed`
- `git diff --check`
  - Passed
- DeepSeek key scan
  - `NO_MATCH`
