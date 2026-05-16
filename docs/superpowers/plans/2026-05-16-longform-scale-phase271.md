# Longform Scale Phase 271 - Writing Task Completion Refresh

## Goal

Close the user-visible loop after Hermes writing controls start a generation task. The frontend must know which background task was queued and refresh chapter content plus writing progress when that task finishes.

## Scope

- Add `task_id` to writing control responses for start, resume, and retry.
- Keep plain writing state reads unchanged.
- Add frontend `WritingState.task_id`.
- Let the project store poll the returned task and refresh returned targets on terminal status.

## RED

- `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing.py -q -k "start_creates_generate_chapter_task"`
  - Failed because `/writing/start` created a task but did not return `task_id`.
- `npm run test:unit -- --run src/stores/project.workspace.test.ts -t "task_id"`
  - Failed because `startWriting()` ignored `task_id` and did not poll `getBackgroundTask`.

## GREEN

- `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing.py -q -k "start_creates_generate_chapter_task"`
  - `1 passed`, `9 deselected`
- `npm run test:unit -- --run src/stores/project.workspace.test.ts -t "task_id"`
  - `1 passed`, `24 skipped`

## Related Verification

- `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing.py backend\tests\test_background.py -q`
  - `41 passed`
- `npm run test:unit -- --run src/stores/project.workspace.test.ts src/components/workspace/workspaceMeta.test.ts src/views/HermesView.test.ts`
  - `28 passed`

## Full Verification

- `backend\.venv\Scripts\python.exe -m pytest backend\tests -q`
  - `660 passed`
- `npm run build`
  - `vue-tsc --noEmit && vite build` passed
- `npm run test:unit -- --run`
  - `64 passed`, `431 passed`
- `git diff --check`
  - Passed
- DeepSeek key scan
  - `NO_MATCH`
