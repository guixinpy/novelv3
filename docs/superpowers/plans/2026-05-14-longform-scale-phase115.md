# Phase 115 - Batch Revision List Feedback

## Goal
Keep chapter revision history responsive when longform projects accumulate many revisions with annotations and corrections.

## Changes
- Revision list pages now load annotations and corrections in two bulk queries for the current page.
- Revision detail behavior remains unchanged.
- Revision list totals now use explicit `count(ChapterRevision.id)`.

## Verification
- Added SQL-level regression coverage proving a 4-revision page uses one annotation query and one correction query.
- Re-ran chapter revision tests: `16 passed`.
- Re-ran the full backend pytest suite: `539 passed`.

## Rejected Retrieval Experiment
- Tested increasing retrieval write batches from `200` to `500` and `1000`.
- Both passed focused batching tests, but million-word smoke regressed compared with Phase 114, so the change was not kept.
- Tested deterministic embedding ids; smoke also regressed, so the change was not kept.
