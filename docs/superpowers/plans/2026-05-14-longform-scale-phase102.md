# Phase 102 - Light Proposal Bundle Counts

## Goal
Keep world-model proposal bundle lists responsive as long projects accumulate large review summaries.

## Changes
- `GET /world-model/proposal-bundles` now computes totals with explicit `count(WorldProposalBundle.id)`.
- Existing filters, item-status subquery, ordering, paginated bundle rows, and response shape are unchanged.

## Verification
- Added SQL-level regression coverage proving bundle-list count queries do not select `WorldProposalBundle.summary`.
- Re-ran focused proposal bundle tests and the complete world frontend API test file.
- Re-ran the full backend pytest suite: `527 passed`.
