# Phase 110 - Light Background Task Counts

## Goal
Keep background task history pagination responsive as long-running projects accumulate task payloads, results, and error text.

## Changes
- `GET /background-tasks` now computes totals with explicit `count(BackgroundTask.id)`.
- Existing project validation, ordering, pagination, task rows, UI hints, and task detail behavior are unchanged.

## Verification
- Added SQL-level regression coverage proving task-list count queries do not select `payload`, `result`, or `error`.
- Re-ran background task tests: `20 passed`.
- Re-ran the full backend pytest suite: `535 passed`.
