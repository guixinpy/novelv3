# Longform Scale Phase 70

## Goal

Make longform maintenance repair efficient when a large project is missing many memory records.

## Success Criteria

1. Small repair backlogs still honor `repair_limit` batching.
2. Large missing or stale memory backlogs rebuild longform memory in one pass.
3. The rebuilt memories are synchronized into retrieval documents.
4. Maintenance diagnostics returns current after the large repair.

## Steps

1. Add a failing repair test that rejects per-chapter refresh for a large missing backlog.
2. Add a large-backlog rebuild threshold.
3. Reuse `rebuild_longform_memory` for large backlogs.
4. Sync all rebuilt longform memory IDs into retrieval.
5. Run targeted maintenance tests.
