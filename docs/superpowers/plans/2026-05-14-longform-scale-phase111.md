# Phase 111 - Light Background Task List Rows

## Goal
Keep background task history pages responsive when long-running projects accumulate large task payloads, results, and errors.

## Changes
- `GET /background-tasks` now projects only the fields shown in the task list.
- Task detail behavior remains unchanged and still exposes payload/result/error where needed.

## Verification
- Added SQL-level regression coverage proving list-row queries do not select `payload`, `result`, or `error`.
- Re-ran background task tests: `21 passed`.
- Re-ran the full backend pytest suite: `536 passed`.
