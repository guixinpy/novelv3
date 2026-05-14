# Phase 94 - Light Model Trace Lists

## Goal

Keep model-call trace history usable on long projects by preventing the list endpoint from loading large prompt payload JSON.

## Changes

- `GET /model-call-traces` now selects only list-summary fields.
- Replaced entity `count()` with explicit `count(id)` to avoid count subqueries selecting `messages`, `context_blocks`, and `trace_metadata`.
- Detail endpoint behavior is unchanged and still returns full trace payloads.

## Verification

- Added SQL-level regression coverage proving the list endpoint does not select trace payload JSON columns.
- Re-ran the complete model-call trace test suite.
