# Phase 105 - Light Review Queue Counts

## Goal
Keep proposal review queues responsive as long projects accumulate large pending candidate facts.

## Changes
- `build_proposal_review_queue` now computes `total_items` with explicit `count(WorldProposalItem.id)`.
- Queue filtering, risk ordering, cluster formation, limit handling, and Athena facade responses are unchanged.

## Verification
- Added SQL-level regression coverage proving review-queue count queries do not select proposal item JSON/text fields.
- Re-ran review queue tests through the world-model and Athena facade routes.
- Re-ran the complete world frontend API test file: `33 passed`.
- Re-ran the full backend pytest suite: `530 passed`.
