# Phase 98 - Light Timeline Counts

## Goal

Keep Athena timeline pagination efficient for long projects by preventing count queries from selecting large world-event payload columns.

## Changes

- `GET /athena/state/timeline` now computes anchor and event totals with explicit `count(id)` queries.
- The paginated timeline data query is unchanged and still returns the payload-derived event descriptions required by the UI.

## Verification

- Added SQL-level regression coverage proving timeline count queries do not select `WorldEvent.primitive_payload` or `WorldEvent.notes`.
- Re-ran focused timeline tests and the complete world frontend API test file.
- Re-ran the full backend pytest suite.
