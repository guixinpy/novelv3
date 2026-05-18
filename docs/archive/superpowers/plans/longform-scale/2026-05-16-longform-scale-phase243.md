# Phase 243 - Stable Lightweight Athena Timeline Windows

## Goal

Make Athena timeline windows safer for large projects by keeping pagination order
stable and avoiding non-display heavy fields in the timeline row queries.

## TDD Evidence

- RED:
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_world_frontend_api.py -q -k "athena_timeline_rows_do_not_select_non_display_heavy_fields or athena_timeline_forward_window_uses_stable_tie_breakers"`
  - Failed because timeline row queries selected unnecessary heavy fields.
  - Failed because forward timeline SQL did not include explicit `anchor_id` / `event_id` tie-breakers.
- GREEN:
  - Same focused command passed with `2 passed`.
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_world_frontend_api.py -q` passed with `46 passed`.

## Changes

- Projected Athena timeline anchors to display fields only.
- Projected Athena timeline events to display fields only.
- Added `anchor_id` as the forward and latest anchor tie-breaker.
- Added `event_id` as the forward event tie-breaker.

## Verification

Full verification is required before committing this phase:

- `backend\.venv\Scripts\python.exe -m pytest backend/tests -q`
- `npm run build`
- `npm run test:unit -- --run`
- `git diff --check`
- DeepSeek key scan must return `NO_MATCH`.
