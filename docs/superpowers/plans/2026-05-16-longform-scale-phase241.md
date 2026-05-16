# Phase 241 - Merge Split Review Queue Clusters

## Goal

Prevent duplicate review queue rows when the same logical review cluster is split
across paginated backend windows. This matters for long-form projects because a
single batch-review category can span many chapters and would otherwise appear as
multiple repeated groups after loading more.

## TDD Evidence

- RED:
  - `npm run test:unit -- --run src/stores/worldModel.test.ts`
  - Failed because the same `cluster_id` from two queue windows produced two rendered store clusters.
- GREEN:
  - Same targeted command passed with `32 passed`.

## Changes

- Added cluster merge logic keyed by `cluster_id`.
- Merged `item_ids`, `bundle_ids`, and `subject_refs` with stable de-duplication.
- Expanded merged chapter ranges from the earliest start to the latest end.
- Kept item-window pagination metadata independent from merged cluster count.

## Verification

Full verification is required before committing this phase:

- `backend\.venv\Scripts\python.exe -m pytest backend/tests -q`
- `npm run build`
- `npm run test:unit -- --run`
- `git diff --check`
- DeepSeek key scan must return `NO_MATCH`.
