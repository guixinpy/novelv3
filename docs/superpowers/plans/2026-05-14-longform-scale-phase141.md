# Phase 141 - Compact background task polling

## Goal

Make frontend background-task polling use a compact task detail response so frequent polling does not fetch large task `payload`, `result`, or `error` fields.

## Why

Long-form workflows can leave many tasks and large task payloads/results. Polling the full task detail every second is unnecessary for the UI path that only needs status and refresh targets.

## TDD

RED:

- `test_get_background_task_compact_does_not_select_heavy_task_fields` expected `?compact=true` task details to omit heavy fields and not select `payload/result/error`.
- `chat.workspace.test.ts` expected task polling to call `getBackgroundTask(taskId, { compact: true })`.
- Both failed because the backend ignored `compact` and the frontend called the full endpoint.

GREEN:

- Added `compact=true` support to `/api/v1/background-tasks/{task_id}` using a projected query.
- Compact responses return `payload/result/error` as `null` while preserving status, UI hint, refresh targets, and timestamps.
- Added optional compact query support to the frontend API client.
- Updated chat polling to request compact task details.

## Verification

- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_background.py::test_get_background_task_compact_does_not_select_heavy_task_fields -q`
- `npm run test:unit -- src/stores/chat.workspace.test.ts`
- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_background.py -q`
- `npm run test:unit -- src/stores/chat.workspace.test.ts src/stores/project.workspace.test.ts`
- `npm run build`
