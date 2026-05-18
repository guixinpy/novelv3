# Phase 104 - Light Dashboard Pending Counts

## Goal
Keep the world-model dashboard responsive when long projects accumulate many large proposal items.

## Changes
- Dashboard pending item totals now use explicit `count(WorldProposalItem.id)`.
- Dashboard pending bundle totals now use explicit `count(distinct(WorldProposalItem.bundle_id))`.
- Current-profile filters and actionable statuses remain unchanged.

## Verification
- Added SQL-level regression coverage proving dashboard pending-count queries do not select proposal item JSON/text fields.
- Re-ran the complete world frontend API test file: `32 passed`.
- Re-ran the full backend pytest suite: `529 passed`.
