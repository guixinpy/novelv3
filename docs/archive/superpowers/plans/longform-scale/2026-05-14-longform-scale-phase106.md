# Phase 106 - Light Athena Boundary Counts

## Goal
Keep Athena dialog context-boundary construction cheap for long projects with many indexed documents, confirmed facts, and pending proposals.

## Changes
- Context-boundary retrieval, confirmed-truth, pending-bundle, and pending-item totals now use explicit `count(id)` queries.
- Existing current-profile filtering and generated boundary text remain unchanged.

## Verification
- Added SQL-level regression coverage proving context-boundary count queries do not select large retrieval/world/proposal columns.
- Re-ran Athena dialog tests: `21 passed`.
- Re-ran the full backend pytest suite: `531 passed`.
