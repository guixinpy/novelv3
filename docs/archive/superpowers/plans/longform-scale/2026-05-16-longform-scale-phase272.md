# Longform Scale Phase 272 - Reuse Active Writing Tasks

## Goal

Prevent duplicate same-chapter generation jobs from repeated writing-control requests. Thousand-chapter projects need idempotent queue behavior to avoid overlapping writes and confusing progress state.

## Scope

- Before creating a `generate_chapter` task from writing controls, look for an active task for the same project and chapter.
- Reuse the active task and return its `task_id`.
- Do not restart `LocalTaskRunner` for a reused task.

## RED

- `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing.py -q -k "reuses_active_generate_chapter_task"`
  - Failed because two consecutive `/writing/start` calls created two `generate_chapter` tasks for chapter 1.

## GREEN

- `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing.py -q -k "reuses_active_generate_chapter_task"`
  - `1 passed`, `10 deselected`

## Related Verification

- `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing.py backend\tests\test_background.py -q`
  - `42 passed`

## Full Verification

- `backend\.venv\Scripts\python.exe -m pytest backend\tests -q`
  - `661 passed`
- `npm run build`
  - `vue-tsc --noEmit && vite build` passed
- `npm run test:unit -- --run`
  - `64 passed`, `431 passed`
- `git diff --check`
  - Passed
- DeepSeek key scan
  - `NO_MATCH`
