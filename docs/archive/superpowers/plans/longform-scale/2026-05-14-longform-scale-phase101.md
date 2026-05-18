# Phase 101 - Light World Fact List Counts

## Goal

Keep the world-model fact ledger responsive for long projects by preventing fact-list pagination totals from selecting large fact JSON columns.

## Changes

- `GET /world-model/facts` now computes totals with explicit `count(WorldFactClaim.id)`.
- Existing filters, ordering, paginated claim rows, and response shape are unchanged.

## Verification

- Added SQL-level regression coverage proving fact-list count queries do not select `object_ref_or_value`, `disclosed_to_refs`, `evidence_refs`, or `notes`.
- Re-ran focused fact-list tests and the complete world frontend API test file.
- Re-ran the full backend pytest suite.
