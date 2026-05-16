# Phase 258 - Recover Running Task Polling From History

## Goal

When the app reloads with a running action in chat history, preserve the
`task_id` and poll the background task endpoint directly. Long-running
generation and maintenance jobs can then surface restart/interruption failures
instead of waiting for history polling to time out.

## TDD Evidence

- RED:
  - `npm run test:unit -- --run src/stores/chat.workspace.test.ts -t "从历史恢复带 task_id"`
  - Failed because `getBackgroundTask('task-recovered', { compact: true })` was
    never called.
- GREEN:
  - Same focused command passed with `1 passed`.
  - `npm run test:unit -- --run src/stores/chat.workspace.test.ts` passed with
    `24 passed`.

## Changes

- Replaced action-only recovery with recovery metadata containing
  `actionType` and optional `taskId`.
- `initFromWorkspaceBootstrap()` now uses compact task polling when recovered
  history includes a `task_id`.
- Existing history-only polling remains the fallback for older action records
  without task IDs.

## Verification Evidence

- `backend\.venv\Scripts\python.exe -m pytest backend/tests -q` passed with
  `651 passed in 54.34s`.
- `npm run build` passed.
- `npm run test:unit -- --run` passed with `62 passed` files and `420 passed`
  tests.
- `git diff --check` passed.
- DeepSeek key scan returned `NO_MATCH`.
