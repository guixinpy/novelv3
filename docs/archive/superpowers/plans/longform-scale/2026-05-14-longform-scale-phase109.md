# Phase 109 - Light Consistency Issue Counts

## Goal
Keep consistency issue pagination responsive as long projects accumulate many text-heavy checks.

## Changes
- `GET /consistency/issues` now computes totals with explicit `count(ConsistencyCheck.id)`.
- Existing project validation, ordering, pagination, response shape, and issue row contents are unchanged.

## Verification
- Added SQL-level regression coverage proving issue-list count queries do not select `description`, `evidence`, or `suggested_fix`.
- Re-ran consistency tests: `7 passed`.
- Re-ran the full backend pytest suite: `534 passed`.
