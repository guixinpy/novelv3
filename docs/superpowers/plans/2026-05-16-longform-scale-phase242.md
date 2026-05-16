# Phase 242 - Lightweight Proposal Review Queue Rows

## Goal

Reduce review queue memory and database I/O by avoiding heavy proposal item
fields when building queue clusters. The queue only needs identifiers, bundle
ids, chapter indexes, predicates, and subject refs.

## TDD Evidence

- RED:
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_world_frontend_api.py -q`
  - Failed because the row query selected `object_ref_or_value` and other heavy fields.
- GREEN:
  - Same targeted command passed with `44 passed`.

## Changes

- Changed `build_proposal_review_queue()` from ORM entity loading to explicit column projection.
- Kept existing risk, grouping, ordering, offset, and `has_more` behavior intact.
- Added a regression test that captures SQL and rejects heavy row fields:
  - `object_ref_or_value`
  - `disclosed_to_refs`
  - `evidence_refs`
  - `notes`

## Verification

Full verification is required before committing this phase:

- `backend\.venv\Scripts\python.exe -m pytest backend/tests -q`
- `npm run build`
- `npm run test:unit -- --run`
- `git diff --check`
- DeepSeek key scan must return `NO_MATCH`.
