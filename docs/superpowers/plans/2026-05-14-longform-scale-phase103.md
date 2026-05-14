# Phase 103 - Light Proposal Detail Item Counts

## Goal
Keep proposal bundle detail pages responsive when long projects accumulate many heavy candidate facts.

## Changes
- `GET /world-model/proposal-bundles/{bundle_id}` now computes `items_total` with explicit `count(WorldProposalItem.id)`.
- Existing bundle binding filters, item ordering, item pagination, reviews, impact snapshots, and conflict detection are unchanged.

## Verification
- Added SQL-level regression coverage proving bundle-detail item count queries do not select `object_ref_or_value`, `disclosed_to_refs`, `evidence_refs`, or `notes`.
- Re-ran the complete world frontend API test file: `31 passed`.
- Re-ran the full backend pytest suite: `528 passed`.
